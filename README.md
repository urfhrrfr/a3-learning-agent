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

- Milestone 1-3：后端 API、MockLLMProvider、多智能体 Orchestrator 已实现。
- Milestone 4：人工智能导论 12 章知识库和 60 道题目草案已准备。
- Milestone 5-7：前端核心页面、组件、资源展示、路径和评估闭环已实现。
- Milestone 8：交付文档、PPT 大纲和 7 分钟演示脚本已准备。
