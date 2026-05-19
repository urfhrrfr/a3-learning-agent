# Backend

FastAPI 后端负责学习画像更新、多智能体资源生成、任务状态管理、学习路径规划、智能辅导、练习评估和状态持久化。

## 启动

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger：http://127.0.0.1:8000/docs

健康检查：http://127.0.0.1:8000/api/health

## 配置

默认演示配置：

```env
LLM_PROVIDER=mock
MYSQL_URL=mysql+pymysql://a3:123456@127.0.0.1:3306/a3_learning?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
VECTOR_STORE=memory
```

真实模型接入可使用：

- `LLM_PROVIDER=spark`
- `LLM_PROVIDER=deepseek`
- `LLM_PROVIDER=qwen`
- `LLM_PROVIDER=dashscope`
- `LLM_PROVIDER=openai_compatible`

Redis 是缓存增强项：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

未配置 Redis 时，系统自动使用数据库 + 内存状态运行。未配置 `MYSQL_URL` 时，持久化层回退到 `backend/data/app.db`。

## 数据存储

- MySQL：画像、任务、资源、学习路径、评估报告、检索日志、历史版本
- SQLite：本地 fallback 与迁移来源
- Redis：任务进度、Agent Trace 和资源快照缓存
- Vector Store：默认内存向量库，可选 Chroma

## 验证

```bash
cd backend
.\.venv\Scripts\python.exe scripts\check_mysql_redis.py
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py --verify-only
.\.venv\Scripts\python.exe -m pytest
```

当前测试结果：`44 passed`

## 真实模型 Provider 配置

后端默认 `LLM_PROVIDER=mock`，用于无 Key、无网络时稳定演示。要切到讯飞星火直连 provider，在 `backend/.env` 或当前终端配置：

```env
LLM_PROVIDER=spark
LLM_TIMEOUT_SECONDS=20
SPARK_APP_ID=your_spark_app_id
SPARK_API_KEY=your_spark_api_key
SPARK_API_SECRET=your_spark_api_secret
SPARK_MODEL=generalv3.5
SPARK_API_URL=wss://spark-api.xf-yun.com/v3.5/chat
```

也可以使用星火 OpenAI-compatible 接口：

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_API_KEY=your_spark_api_password
OPENAI_COMPATIBLE_BASE_URL=https://spark-api-open.xf-yun.com/v1
OPENAI_COMPATIBLE_MODEL=4.0Ultra
```

启动：

```bash
cd backend
uvicorn app.main:app --reload
```

调用真实模型的接口：`/api/profile/chat`、`/api/resources/generate/background`、`/api/tutor/chat`、`/api/quiz/submit`。如果真实模型 Key 缺失、网络失败、超时、返回空内容、返回结构不符合 JSON/内容契约，系统会保留业务响应并进入 fallback，不会因为模型失败直接让这些核心接口 500。

验证不是 mock：`GET /api/health` 返回 `llm_provider=spark` 或 `openai_compatible` 且 `mock_llm=false`；资源生成 job 的 `traces[].llm_provider`、辅导接口的 `llm_provider` 也应显示真实 provider。若看到 `used_fallback=true`、`fallback_reason` 或 trace warnings，说明真实模型路径已被尝试但本次触发了兜底。

## Vector Store / Chroma

RAG defaults to the in-memory vector store so the project runs without extra services:

```env
VECTOR_STORE=memory
```

To verify the real Chroma path locally, install the optional dependency and enable it:

```powershell
cd backend
.\.venv\Scripts\pip install chromadb
$env:VECTOR_STORE="chroma"
$env:CHROMA_PERSIST_DIR=".chroma"
.\.venv\Scripts\python -m pytest
```

`GET /api/health` returns `vector_store.requested`, `vector_store.active`, `vector_store.fallback`, and `vector_store.collection`. If Chroma is unavailable, the backend falls back to memory instead of failing to start.

## MySQL + Redis

For a local durable storage stack:

```powershell
cd backend
docker compose -f docker-compose.storage.yml up -d
```

Set these values in `backend/.env`:

```env
MYSQL_URL=mysql+pymysql://a3:123456@127.0.0.1:3306/a3_learning?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
```

Verify both services:

```powershell
.\.venv\Scripts\python.exe scripts\check_mysql_redis.py
```

Migrate or verify SQLite data:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py --verify-only
```
