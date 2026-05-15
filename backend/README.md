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
REDIS_URL=
```

真实模型接入可使用：

- `LLM_PROVIDER=spark`
- `LLM_PROVIDER=deepseek`
- `LLM_PROVIDER=qwen`
- `LLM_PROVIDER=dashscope`
- `LLM_PROVIDER=openai_compatible`

Redis 是可选增强项：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

未配置 Redis 时，系统自动使用 SQLite + 内存状态运行。

## 数据存储

- SQLite：画像、任务、资源、学习路径、评估报告、历史版本
- Redis 可选缓存：任务进度、Agent Trace 和资源快照
- 任务读取顺序：内存运行态 -> Redis 快照 -> SQLite 持久化

## 验证

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

当前测试结果：`28 passed`
