# 🚀 用户认证服务 - Render 部署指南

## 📁 项目结构

```
deploy/
├── main.py           # 主应用文件
├── requirements.txt  # 依赖列表
└── render.yaml       # Render 配置文件
```

## 📋 部署步骤

### 步骤 1: 创建 GitHub/GitLab 仓库

1. 在 GitHub 或 GitLab 创建一个新仓库
2. 将 `deploy/` 目录下的所有文件上传到仓库
3. 确保仓库是公开的（或配置 Render 访问权限）

### 步骤 2: 登录 Render

1. 访问 [Render 官网](https://render.com)
2. 使用 GitHub 账号登录

### 步骤 3: 创建 Web Service

1. 点击左上角 **New** -> **Web Service**
2. 选择你的 GitHub 仓库
3. 配置项目：
   - **Name**: `user-auth-service`
   - **Region**: 选择离你最近的区域（如 Singapore）
   - **Branch**: `main`
   - **Root Directory**: 留空（或输入 `deploy` 如果文件在子目录）

### 步骤 4: 配置构建和启动

Render 会自动检测 Python 项目并使用 `pip install -r requirements.txt`

如果需要手动配置：
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 步骤 5: 添加环境变量

在 **Environment** 标签页添加：
- `SECRET_KEY`: 点击 **Generate** 生成随机密钥
- `PYTHON_VERSION`: `3.11.5`

### 步骤 6: 部署

点击 **Create Web Service** 开始部署

## 🔗 部署完成后

### 访问地址
- **服务地址**: `https://user-auth-service-xxx.onrender.com`
- **API 文档**: `https://user-auth-service-xxx.onrender.com/docs`
- **健康检查**: `https://user-auth-service-xxx.onrender.com/health`

### 测试接口

```bash
# 注册用户
curl -X POST https://your-service-url.onrender.com/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# 用户登录
curl -X POST https://your-service-url.onrender.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# 获取用户信息
curl -X GET https://your-service-url.onrender.com/user/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🌐 API 接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/register` | POST | 用户注册 |
| `/login` | POST | 用户登录 |
| `/user/profile` | GET | 获取用户信息（需Token） |
| `/verify-token` | POST | 验证Token |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API文档 |

## ⚠️ 注意事项

1. **免费额度**: Render 免费版每月 750 小时，足够小型应用使用
2. **休眠机制**: 免费版 15 分钟无请求会自动休眠，首次请求可能较慢
3. **数据库**: 使用 SQLite，数据存储在容器内（重启会丢失）
4. **SSL**: Render 自动提供 HTTPS

## 💾 数据持久化（可选）

如果需要数据持久化，建议使用外部数据库：

- Render PostgreSQL（免费额度有限）
- Supabase（免费层可用）
- PlanetScale（MySQL，免费层可用）

修改 `main.py` 中的数据库连接：

```python
# 使用 PostgreSQL
import psycopg2
conn = psycopg2.connect(os.getenv("DATABASE_URL"))

# 使用 SQLite（当前配置）
conn = sqlite3.connect(str(DATABASE_PATH))
```

## 🔧 管理命令

```bash
# 查看日志
# 在 Render 控制台点击 "Logs"

# 重启服务
# 在 Render 控制台点击 "Manual Deploy" -> "Deploy latest commit"

# 查看部署状态
# 在 Render 控制台查看
```

## ✅ 部署检查清单

- [ ] 代码已上传到 GitHub/GitLab
- [ ] Render 已连接到仓库
- [ ] 环境变量 `SECRET_KEY` 已设置
- [ ] 构建命令正确配置
- [ ] 启动命令正确配置
- [ ] 健康检查接口返回 `{"status": "ok"}`
- [ ] API 文档可访问

---

🎉 **部署成功！** 你的用户认证服务已经上线运行！
