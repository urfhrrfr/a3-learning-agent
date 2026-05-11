# LLM Provider 接入说明

本项目默认使用 `MockLLMProvider`，保证没有真实模型 Key 时也能稳定演示。系统已新增真实 LLM Provider 架构，可以通过环境变量切换到科大讯飞星火或 OpenAI 兼容模型。部分 Agent 会优先调用真实模型，失败时自动回退到本地模板。

## 1. Provider 类型

| Provider | 环境变量 | 用途 |
| --- | --- | --- |
| MockLLMProvider | `LLM_PROVIDER=mock` | 默认兜底，稳定演示，不需要 Key |
| SparkLLMProvider | `LLM_PROVIDER=spark` | 用于接入科大讯飞星火 |
| OpenAICompatibleProvider | `LLM_PROVIDER=openai_compatible` | 兼容 OpenAI、DeepSeek、Qwen/百炼兼容模式等 |

也支持这些别名：

```text
LLM_PROVIDER=openai
LLM_PROVIDER=deepseek
LLM_PROVIDER=qwen
LLM_PROVIDER=dashscope
```

这些别名都会走 `OpenAICompatibleProvider`，通过 `OPENAI_COMPATIBLE_BASE_URL` 和 `OPENAI_COMPATIBLE_MODEL` 区分实际模型平台。

## 2. 默认 Mock 模式

```env
LLM_PROVIDER=mock
```

适合：

- 本地无 Key 开发；
- 录屏和答辩兜底；
- 自动化测试。

## 3. 科大讯飞星火模式

```env
LLM_PROVIDER=spark
SPARK_APP_ID=your_app_id
SPARK_API_KEY=your_api_key
SPARK_API_SECRET=your_api_secret
SPARK_MODEL=generalv3.5
SPARK_API_URL=https://spark-api.xf-yun.com/v3.5/chat
```

说明：

- `SparkLLMProvider` 是科大讯飞星火接入边界。
- 不同星火产品和版本可能使用不同 endpoint 或 WebSocket 协议。
- 如果后续改用 WebSocket，只需要替换 `SparkLLMProvider.complete()` 内部实现，不影响业务接口。

## 4. OpenAI 兼容模式

OpenAI：

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_API_KEY=your_key
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini
```

DeepSeek：

```env
LLM_PROVIDER=deepseek
OPENAI_COMPATIBLE_API_KEY=your_deepseek_key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
OPENAI_COMPATIBLE_MODEL=deepseek-chat
```

阿里云百炼 / Qwen 兼容模式：

```env
LLM_PROVIDER=dashscope
OPENAI_COMPATIBLE_API_KEY=your_dashscope_key
OPENAI_COMPATIBLE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_COMPATIBLE_MODEL=qwen-plus
```

## 5. 健康检查

启动后访问：

```text
GET /api/health
```

返回中会包含：

```json
{
  "ok": true,
  "data": {
    "status": "healthy",
    "mock_llm": true,
    "llm_provider": "mock",
    "course": "人工智能导论"
  },
  "error": null
}
```

## 6. 哪些模块会调用真实模型

当 `LLM_PROVIDER` 不是 `mock` 时，以下模块会优先调用 `llm.complete()`：

| 模块 | 调用用途 | 失败回退 |
| --- | --- | --- |
| ProfileAgent | 从自然语言中抽取画像字段 | 关键词规则抽取 |
| LectureAgent | 生成个性化讲解文档 | 本地讲解模板 |
| QuizAgent | 生成分层练习题 JSON | 本地题库模板 |
| ReviewAgent | 对资源内容做事实校验辅助判断 | 本地规则审核 |
| AssessmentAgent | 生成学习效果评估 | 本地规则评估 |
| Tutor API | 生成智能辅导回答 | 本地固定回答模板 |

每个 Agent Trace 会返回 `llm_provider` 字段，例如：

```json
{
  "agent": "LectureAgent",
  "llm_provider": "spark",
  "status": "completed"
}
```

说明：

- `mock` 模式下不会访问外部模型，适合测试和演示兜底。
- `spark`、`openai_compatible` 等真实模式下，如果模型请求失败，会记录 warning 并回退模板。
- 前端可以通过 Agent Trace 展示当前生成流程使用的是哪个 Provider。

答辩时可以说明：

> 系统默认 Mock 保证稳定演示，同时已经抽象出真实 LLM Provider，可以通过环境变量切换到科大讯飞星火或 OpenAI 兼容模型。业务接口不依赖具体模型厂商，因此后续扩展成本较低。
