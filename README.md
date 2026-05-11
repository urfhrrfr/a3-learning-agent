# A3 个性化学习资源生成多智能体系统

面向“人工智能导论”课程的 Python + Vue MVP。系统支持对话式学习画像、多智能体资源生成、Agent Trace、个性化学习路径、智能辅导和练习评估闭环。

## 本地启动

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

访问：

- 前端：http://127.0.0.1:5173
- 后端 Swagger：http://127.0.0.1:8000/docs

## MVP 闭环

1. `/profile` 通过对话更新学习画像。
2. `/generate` 发起资源生成，查看进度和 Agent Trace。
3. `/resources` 查看 6 类资源：讲解、导图、练习、阅读、视频脚本、代码案例。
4. `/path` 查看个性化学习路径和推荐理由。
5. `/assessment` 提交练习，生成评估报告并调整路径。
6. `/tutor` 基于画像和资源进行 Mock 智能辅导。

## 当前状态

- 后端 API、MockLLMProvider、多智能体 Orchestrator、SQLite 状态恢复已实现。
- 人工智能导论 12 章知识库和 60 道题目草案已准备。
- 前端核心页面、资源展示、Agent Trace、学习路径、辅导和评估闭环已实现。
- 前端已补充全局状态、空状态、错误状态、公共资源渲染组件和 Mermaid 按需加载。
- 交付文档、PPT 大纲、7 分钟演示脚本、答辩 Runbook 已准备。

## 演示交付材料

- 演示 Runbook：`docs/delivery/demo-runbook.md`
- 7 分钟视频脚本：`docs/delivery/demo-video-script.md`
- PPT 大纲：`docs/delivery/ppt-outline.md`
- 答辩手册：`docs/delivery/presentation-and-defense-guide.md`
- 最终检查清单：`docs/delivery/final-checklist.md`
- API 接口契约：`docs/api-contract.md`
- LLM Provider 接入说明：`docs/llm-provider.md`

## 验证命令

后端：

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

前端：

```bash
cd frontend
npm run build
```
