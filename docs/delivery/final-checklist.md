# 最终交付检查清单

本文档用于项目提交前的最后自检，覆盖 API 契约、后端接口、前端联调、演示路径和已知限制。

## 1. 交付物

| 交付物 | 路径 | 状态 |
| --- | --- | --- |
| API 接口契约 | `docs/api-contract.md` | 已完成 |
| 后端接口测试 | `backend/tests/test_api.py` | 已补充契约结构测试 |
| 前端 API 封装 | `frontend/src/api.ts` | 已对齐契约 |
| 前端类型定义 | `frontend/src/types.ts` | 已补齐核心类型 |
| 前端状态管理 | `frontend/src/store.ts` | 已接入 typed API |
| 测试说明 | `docs/delivery/test-guide.md` | 已存在 |
| 演示视频脚本 | `docs/delivery/demo-video-script.md` | 已整理 |
| 演示 Runbook | `docs/delivery/demo-runbook.md` | 已完成 |
| PPT 大纲 | `docs/delivery/ppt-outline.md` | 已整理 |
| 答辩手册 | `docs/delivery/presentation-and-defense-guide.md` | 已完成 |
| 提交说明 | `docs/delivery/submission-summary.md` | 已完成 |

## 2. 本地启动

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 后端 Swagger：`http://127.0.0.1:8000/docs`

## 3. 自动化验证

后端测试：

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

预期结果：

```text
6 passed
```

前端构建：

```bash
cd frontend
npm run build
```

预期结果：

```text
vue-tsc -b && vite build 成功
```

说明：Mermaid 已改为按需加载，生产构建可通过。项目保留较高 chunk warning 阈值，用于避免懒加载可视化库在交付时产生误导性警告。

## 4. 接口契约自检

以下接口应全部可用，并返回统一结构 `{ ok, data, error }`：

- `GET /api/health`
- `POST /api/profile/chat`
- `GET /api/profile/current`
- `POST /api/resources/generate`
- `GET /api/jobs/{job_id}`
- `GET /api/resources`
- `GET /api/resources/{resource_id}`
- `POST /api/learning-path/generate`
- `GET /api/learning-path/current`
- `POST /api/tutor/chat`
- `POST /api/quiz/submit`
- `GET /api/assessment/report`

字段结构以 `docs/api-contract.md` 为准。后端测试已覆盖这些接口的主要返回字段。

## 5. 页面联调清单

逐页手动检查：

| 页面 | 路由 | 检查点 |
| --- | --- | --- |
| 工作台 | `/` | 能展示画像、路径、最近资源；点击生成资源无报错 |
| 学习画像 | `/profile` | 能加载画像；提交画像对话后画像版本更新 |
| 资源生成 | `/generate` | 点击生成后展示进度、Agent Trace 和生成资源 |
| 资源库 | `/resources` | 能展示资源列表；筛选和点击资源详情正常 |
| 学习路径 | `/path` | 能展示路径步骤、推荐资源 ID 和预计时间 |
| 智能辅导 | `/tutor` | 提问后能展示回答和 Mermaid 图 |
| 练习评估 | `/assessment` | 提交练习后能展示分数、反馈和调整后的路径 |

## 6. 推荐演示流程

更详细的现场步骤见 `docs/delivery/demo-runbook.md`。

1. 打开 `http://127.0.0.1:5173`，展示工作台总览。
2. 进入 `/profile`，输入学习情况：

```text
我线性代数比较薄弱，希望多给 Python 代码案例和图解。
```

3. 进入 `/generate`，点击生成个性化资源，展示进度、Agent Trace 和资源卡片。
4. 进入 `/resources`，查看讲解、导图、练习、阅读、视频脚本和代码案例。
5. 进入 `/path`，展示个性化学习路径、推荐资源和推荐理由。
6. 进入 `/tutor`，提问：

```text
为什么训练准确率高，测试效果仍然可能不好？
```

7. 进入 `/assessment`，提交练习，展示测评报告和路径调整。
8. 回到 `/`，用工作台总览收尾。

## 7. 已知限制

- 当前使用 MockLLMProvider，适合稳定演示，不依赖真实模型 API Key。
- `POST /api/resources/generate` 当前同步完成，但返回结构已经包含 `job`、`status`、`progress` 和 `events`，任务过程会持续落库，后续可平滑切换为真正异步任务。
- 资源列表当前未分页，后续数据量增加时再扩展分页参数。
- 认证当前未启用，后续如接入登录，需要统一补充 `Authorization` header。
- 当前是单用户 MVP，SQLite 用于本地演示状态恢复，生产环境需要更完整的数据模型、认证和权限。

## 8. 提交前最终确认

- [ ] `docs/api-contract.md` 中 12 个接口均已覆盖。
- [ ] `.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider` 通过。
- [ ] `npm run build` 通过。
- [ ] 本地后端 `8000` 正常启动。
- [ ] 本地前端 `5173` 正常启动。
- [ ] `/profile` 到 `/assessment` 的演示闭环能手动走通。
- [ ] 已按 `docs/delivery/demo-video-script.md` 试讲一遍。
- [ ] 已按 `docs/delivery/demo-runbook.md` 完整走一遍现场演示。
- [ ] 已按 `docs/delivery/presentation-and-defense-guide.md` 准备答辩问答。
- [ ] 已阅读 `docs/delivery/submission-summary.md` 并确认提交范围。
- [ ] 若需要提交代码，确认只包含本轮相关变更。
