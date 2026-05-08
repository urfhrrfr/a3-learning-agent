# Backend

FastAPI 后端提供 MockLLM、多智能体编排、资源生成、学习路径、辅导和评估接口。

## 启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## 验证

```bash
pytest
```
