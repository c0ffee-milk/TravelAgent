# Lesson 02：LLM Provider 与自然澄清生成

本节把 Lesson 01 的自然澄清状态接到真实大模型服务。TravelAgent 不再让 LLM 只抽取 `TravelRequest` 字段，而是让 LLM 输出完整的需求理解结果：事实、归一化字段、业务推断、缺失决策、风险和下一步自然追问。

本节默认服务方是 DeepSeek，接口按 OpenAI-compatible Chat Completions 形态设计。

## 本节目标

完成本节后，你应该能够：

- 用统一 Provider 调用 DeepSeek。
- 配置真实 `base_url`、`api_key`、模型名、超时和重试。
- 让 LLM 输出严格 JSON。
- 构造自然澄清 prompt，而不是只构造字段抽取 prompt。
- 理解 `build_natural_clarification_messages()` 如何驱动 demo 对话。

## Provider 层职责

`llm_provider.py` 只负责模型服务和 prompt 构造，不负责 CLI 交互。

它当前包含：

- `LLMConfig`
- `LLMMessage`
- `LLMResponse`
- `DeepSeekChatClient`
- `parse_json_object()`
- `build_travel_request_extraction_messages()`
- `build_natural_clarification_messages()`

其中 `build_travel_request_extraction_messages()` 保留为基础抽取教学对照；当前 demo 主流程使用 `build_natural_clarification_messages()`。

## 真实 API 配置

在 `agent/.env` 中配置：

```dotenv
DEEPSEEK_API_KEY=你的真实 DeepSeek API key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=60
DEEPSEEK_MAX_RETRIES=2
```

测试前可以手动加载：

```bash
cd agent
set -a
source .env
set +a
```

不要打印完整 API key。

## 自然澄清 Prompt

自然澄清 prompt 要求模型输出：

```json
{
  "facts": {},
  "normalized": {},
  "inferred": {},
  "missing_decisions": [],
  "assumptions": [],
  "risks": [],
  "next_action": {
    "type": "ask",
    "question": "...",
    "reason": "..."
  },
  "ready_for_planning": false
}
```

关键规则：

- 一次只问一个最关键问题。
- 不要机械追问所有字段。
- 优先问会改变方案分支的问题。
- 带父母、老人、儿童、孕妇同行时，优先确认体力、步行强度或特殊照顾需求。
- 如果预算是人均，归一化时要估算总预算，并在 `inferred.budget_type` 中标明。
- 目的地是大范围区域时，应追问旅行风格或候选国家/城市。

## 本节要修改的 Agent 模块

本节对应：

- `agent/src/travel_agent/llm_provider.py`
- `agent/scripts/demo_clarification_chat.py`

本节新增或升级：

- `build_natural_clarification_messages()`
- Provider 网络重试和超时配置。
- demo 主流程切换到自然澄清状态。

## 运行 Demo

```bash
cd agent
python scripts/demo_clarification_chat.py
```

示例体验：

```text
你：我明年3月份想去上海旅游
Agent：你从哪个城市出发？这会影响交通时间和预算估算。
你：武汉
Agent：这次大概安排几天？一个人去还是和家人朋友一起？
你：一个周，跟我父母一起
Agent：带父母出行的话，我需要先确认他们的体力和步行接受度。你们希望整体轻松一点，还是可以接受每天多走一些？
```

这说明 Agent 已经开始根据场景提问，而不是只按字段顺序提问。

## 自检标准

完成本节后，你应该能回答：

- 为什么项目删除了表单式 `clarify_request()` 主线？
- `build_natural_clarification_messages()` 和字段抽取 prompt 有什么区别？
- 为什么 LLM 输出必须包含 `facts` 和 `normalized` 两层？
- `next_action.reason` 对调试有什么价值？
- 网络超时时为什么需要 Provider 层重试，而不是 demo 自己重试？

## 参考

- DeepSeek API Docs: https://api-docs.deepseek.com/
- DeepSeek V4 Preview Release: https://api-docs.deepseek.com/news/news260424
