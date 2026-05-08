# 部署说明

## 环境要求

- Python 3.11+
- Node.js 18+
- Windows、macOS 或 Linux 本地环境

## 后端部署

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

生产环境可将 SQLite 路径、模型 Provider 和 CORS 白名单迁移到环境变量。

## 前端部署

```bash
cd frontend
npm install
npm run build
npm run preview
```

如后端不在同域，设置 `VITE_API_BASE=http://后端地址:8000` 后重新构建。

## Mock 与真实模型切换

MVP 默认使用 MockLLMProvider。后续接入科大讯飞具体模型/API 时，鉴权方式、模型名、请求协议以官方文档为准，不在代码中硬编码密钥。
