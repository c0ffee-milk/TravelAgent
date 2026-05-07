# Lesson 02：LLM Provider

本节课开始把 TravelAgent 接到真实大模型服务。你要做的不是在业务代码里到处写 API 请求，而是先建立一个统一的 LLM Provider 层，让后续需求抽取、澄清判断、行程生成都通过同一个入口调用模型。

本节默认服务方是 DeepSeek，接口按 OpenAI-compatible Chat Completions 形态设计。本节目标是接入真实 API，而不是只做 mock。

## 本节目标

完成本节后，你应该能够：

- 理解为什么需要单独的 LLM Provider 层。
- 从环境变量读取 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`。
- 用统一消息结构表达 system/user/assistant 消息。
- 配置真实 `base_url` 和 `api_key`。
- 调用真实 OpenAI-compatible `/chat/completions` 接口。
- 为后续结构化抽取准备稳定的 JSON 输出约束。

## 基础知识

### 1. Provider 层的作用

不要让业务模块直接依赖 DeepSeek 请求细节。否则后续切换模型、添加重试、记录 trace、统计成本都会很难。

Provider 层负责：

- 读取模型配置。
- 拼装 HTTP 请求。
- 统一消息格式。
- 解析模型响应。
- 把错误转成项目内部异常。

业务模块只关心：

```text
输入消息 -> 得到模型文本输出
```

### 2. OpenAI-compatible 接口

DeepSeek 支持 OpenAI-compatible API，因此本节按如下约定封装：

```text
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json
```

请求体核心字段：

```json
{
  "model": "deepseek-v4-flash",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.2
}
```

### 3. 结构化输出

后续需求抽取需要模型输出 JSON。Lesson 02 不直接实现完整抽取逻辑，但会准备一个提示词构造函数，让模型围绕 `TravelRequest` 字段返回结构化草案。

## 真实 API 配置

官方 DeepSeek API 文档当前给出的 OpenAI-compatible 配置为：

```text
base_url=https://api.deepseek.com
model=deepseek-v4-flash
```

可选模型：

- `deepseek-v4-flash`：本课程默认值，适合需求抽取、普通对话和多数 Agent 步骤。
- `deepseek-v4-pro`：适合更复杂的规划、推理和审稿。
- `deepseek-chat`：兼容别名，官方标注将在 2026-07-24 弃用，不建议新代码默认使用。
- `deepseek-reasoner`：兼容别名，官方标注将在 2026-07-24 弃用。

API key 需要你在 DeepSeek API 平台创建。不要把真实 key 写入仓库，不要提交 `.env` 文件。

## 本节要修改的 Agent 模块

本节新增或补齐：

- `agent/src/travel_agent/llm_provider.py`：DeepSeek/OpenAI-compatible LLM Provider。

本节更新：

- `agent/src/travel_agent/README.md`：加入 Lesson 02 模块说明。
- `agent/README.md`：加入 LLM Provider 课程锚点。
- `course/README.md`：加入 Lesson 02 指导书索引。

## 推荐搭建步骤

### Step 1：创建本地环境变量文件

配置样例在：

```text
agent/configs/.env.example
```

在 `agent/` 目录下创建一个本地 `.env` 文件：

```bash
cd agent
cp configs/.env.example .env
```

然后把 `.env` 改成真实配置：

```dotenv
DEEPSEEK_API_KEY=你的真实 DeepSeek API key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.env` 已经被 `.gitignore` 忽略，真实密钥只放本地。

### Step 2：把 `.env` 加载到当前 shell

当前项目暂时不引入 `python-dotenv`，所以 `LLMConfig.from_env()` 只会读取系统环境变量。测试前需要先加载：

```bash
cd agent
set -a
source .env
set +a
```

检查变量是否存在：

```bash
echo "$DEEPSEEK_BASE_URL"
echo "$DEEPSEEK_MODEL"
```

不要在终端里打印完整 `DEEPSEEK_API_KEY`。如果要确认是否加载，可以只看长度：

```bash
python - <<'PY'
import os
print("DEEPSEEK_API_KEY length:", len(os.getenv("DEEPSEEK_API_KEY", "")))
PY
```

### Step 3：阅读并实现 llm_provider.py

重点看这些对象：

- `LLMConfig`：模型配置。
- `LLMMessage`：统一消息结构。
- `LLMResponse`：模型响应。
- `DeepSeekChatClient`：DeepSeek Chat Completions 客户端。
- `build_travel_request_extraction_messages()`：为后续需求抽取准备提示词。

### Step 4：理解错误边界

Provider 层至少要区分两类错误：

- `LLMConfigurationError`：缺少 API key、base_url、model 等配置问题。
- `LLMProviderError`：HTTP 失败、响应格式异常、模型返回不可解析等运行问题。

### Step 5：用 curl 做真实连通性测试

先不依赖 Python 代码，直接确认 key 和 URL 可用：

```bash
curl "$DEEPSEEK_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$DEEPSEEK_MODEL"'",
    "messages": [
      {"role": "system", "content": "你是一个简洁的测试助手。"},
      {"role": "user", "content": "只回复 pong"}
    ],
    "temperature": 0
  }'
```

成功时，响应里应该能看到：

```json
{
  "choices": [
    {
      "message": {
        "content": "pong"
      }
    }
  ]
}
```

如果返回 `401`，通常是 API key 错误或没有加载环境变量。

如果返回模型不存在，检查 `DEEPSEEK_MODEL` 是否为 `deepseek-v4-flash` 或 `deepseek-v4-pro`。

### Step 6：用 Python 做真实 Provider 测试

实现 `llm_provider.py` 后，在 `agent/` 目录运行：

```bash
python - <<'PY'
from travel_agent.llm_provider import DeepSeekChatClient, LLMConfig, LLMMessage

client = DeepSeekChatClient(LLMConfig.from_env())
response = client.chat([
    LLMMessage(role="system", content="你是一个简洁的测试助手。"),
    LLMMessage(role="user", content="只回复 pong"),
], temperature=0)

print(response.content)
PY
```

预期输出接近：

```text
pong
```

### Step 7：测试 JSON 输出

继续测试结构化输出，为后续 `TravelRequest` 抽取做准备：

```bash
python - <<'PY'
from travel_agent.llm_provider import (
    DeepSeekChatClient,
    LLMConfig,
    build_travel_request_extraction_messages,
    parse_json_object,
)

client = DeepSeekChatClient(LLMConfig.from_env())
messages = build_travel_request_extraction_messages(
    "下个月想和女朋友去日本玩 5 天，预算 12000，希望轻松一点。"
)
response = client.chat(
    messages,
    temperature=0,
    response_format={"type": "json_object"},
)

print(response.content)
print(parse_json_object(response.content))
PY
```

如果模型返回的不是合法 JSON，先检查 prompt 是否明确要求“只输出 JSON 对象”，再检查是否传入了 `response_format={"type": "json_object"}`。

## 关键设计取舍

- 本节使用 Python 标准库 `urllib`，暂不引入第三方 SDK，便于理解 HTTP 调用本质。
- 本节不在 `clarification.py` 中直接调用 LLM，避免把 Provider 和业务逻辑过早耦合。
- 本节只准备结构化抽取提示词，不实现完整 `TravelRequest` 自动填充。
- 本节测试真实 API 连通性，但不要把真实 API key 写进任何代码或 Markdown。
- 后续课程可以把 `DeepSeekChatClient` 替换为更完整的 SDK、统一模型网关或测试 mock。

## 自检标准

完成本节后，你应该能回答：

- 为什么不能在业务函数里直接写 DeepSeek 请求？
- `LLMConfig.from_env()` 解决了什么问题？
- 如何配置 `DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`？
- `LLMMessage` 为什么要显式区分 role 和 content？
- 如何用 curl 判断 API key 和 URL 是否可用？
- 如何用 Python 检查 Provider 是否能拿到真实模型响应？
- Provider 层应该暴露什么，隐藏什么？
- Lesson 03 以后工具调用和规划模块应该如何复用这个 Provider？

## 参考

- DeepSeek API Docs: https://api-docs.deepseek.com/
- DeepSeek V4 Preview Release: https://api-docs.deepseek.com/news/news260424
