from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import sqlite3
import jwt
import datetime
from pathlib import Path
import os

app = FastAPI(title="用户认证服务", version="1.0.0")

DATABASE_PATH = Path("./user_database.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def init_database():
    conn = sqlite3.connect(str(DATABASE_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ 用户数据库初始化完成")

def get_db_connection():
    return sqlite3.connect(str(DATABASE_PATH))

def generate_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "valid": True
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "token_expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "invalid_token"}

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    phone: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    token: str

def generate_user_id() -> str:
    import random
    return str(random.randint(100000, 999999))

@app.post("/register", summary="用户注册")
def register(req: RegisterRequest):
    if not req.username or len(req.username) < 3:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "username_too_short", "message": "用户名长度至少为3个字符"}
        )
    
    if not req.password or len(req.password) < 6:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "password_too_short", "message": "密码长度至少为6个字符"}
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (req.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "username_exists", "message": "用户名已存在"}
            )
        
        user_id = generate_user_id()
        
        cursor.execute("INSERT INTO users (user_id, username, password, email, phone) VALUES (?, ?, ?, ?, ?)",
                       (user_id, req.username, req.password, req.email, req.phone))
        
        conn.commit()
        token = generate_token(user_id, req.username)
        
        return {"success": True, "user_id": user_id, "username": req.username, "token": token, "message": "注册成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"success": False, "error": "database_error", "message": str(e)})
    finally:
        conn.close()

@app.post("/login", summary="用户登录")
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, username, password FROM users WHERE username = ?", (req.username,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail={"success": False, "error": "user_not_found", "message": "用户名不存在"})
        
        user_id, stored_username, stored_password = user
        
        if req.password != stored_password:
            raise HTTPException(status_code=401, detail={"success": False, "error": "wrong_password", "message": "密码错误"})
        
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        conn.commit()
        
        token = generate_token(user_id, req.username)
        
        return {"success": True, "user_id": user_id, "username": req.username, "token": token, "message": "登录成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "error": "database_error", "message": str(e)})
    finally:
        conn.close()

def get_current_user(authorization: str = Header(None)) -> Dict:
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": "missing_token", "message": "未提供认证令牌"})
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "invalid_token_format", "message": "令牌格式错误"})
    
    token = authorization[7:]
    payload = verify_token(token)
    
    if not payload.get("valid"):
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "无效或已过期的令牌"})
    
    return payload

@app.get("/user/profile", summary="获取用户信息")
def get_user_profile(current_user: Dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, username, email, phone, created_at, last_login FROM users WHERE user_id = ?",
                       (current_user["user_id"],))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail={"success": False, "message": "用户不存在"})
        
        return {"success": True, "user": {"user_id": user[0], "username": user[1], "email": user[2], 
                                          "phone": user[3], "created_at": user[4], "last_login": user[5]}}
        
    finally:
        conn.close()

@app.post("/verify-token", summary="验证Token")
def verify_token_endpoint(req: TokenRequest):
    result = verify_token(req.token)
    
    if not result.get("valid"):
        return {"success": False, "valid": False, "error": result.get("error"), "message": "Token无效或已过期"}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, username, email, phone FROM users WHERE user_id = ?", (result["user_id"],))
        user = cursor.fetchone()
        
        if user:
            return {"success": True, "valid": True, "user_id": user[0], "username": user[1], "email": user[2], "phone": user[3]}
        else:
            return {"success": False, "valid": False, "error": "user_not_found", "message": "用户不存在"}
        
    finally:
        conn.close()

@app.get("/health", summary="健康检查")
def health_check():
    return {"status": "ok", "service": "user-auth-service"}

@app.get("/admin/users", summary="获取所有用户列表（管理员接口）")
def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT user_id, username, email, phone, created_at, last_login 
            FROM users 
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        
        user_list = []
        for user in users:
            user_list.append({
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "phone": user[3],
                "created_at": user[4],
                "last_login": user[5]
            })
        
        return {
            "success": True,
            "total": len(user_list),
            "users": user_list
        }
        
    finally:
        conn.close()

@app.get("/admin/stats", summary="获取用户统计信息")
def get_user_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_login) = DATE('now')")
        active_today = cursor.fetchone()[0]
        
        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "active_today": active_today
            }
        }
        
    finally:
        conn.close()

init_database()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
