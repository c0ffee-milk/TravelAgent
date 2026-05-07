# TravelAgent Agent Project

本目录是未来完整可独立运行的旅游规划 Agent 工程根目录。

当前状态：已经具备 Lesson 00-02 的最小可对话需求澄清 demo，但还不是完整旅游规划 Agent。

## 目录职责

```text
agent/
  pyproject.toml
  configs/
    .env.example
  src/
    travel_agent/
      __init__.py
      README.md
      schemas.py
      clarification.py
      llm_provider.py
      map_tools.py
  data/
    README.md
    mock/
    knowledge_base/
    eval/
  evals/
    README.md
  scripts/
    README.md
    demo_clarification_chat.py
  app/
    README.md
```

## 当前可运行 Demo

Lesson 00-02 已经可以串成一个 CLI 对话 demo：

```bash
cd agent
python scripts/demo_clarification_chat.py
```

这个 demo 会自动尝试读取 `agent/.env` 或 `agent/configs/.env` 中的 DeepSeek 配置。你也可以手动加载环境变量后运行：

```bash
cd agent
set -a
source .env
set +a
python scripts/demo_clarification_chat.py
```

当前 demo 能做：

- 从用户自然语言中抽取 `TravelRequest` 草案。
- 判断缺失字段。
- 生成一轮或多轮澄清问题。
- 在信息足够时提示可以进入初版规划。

当前 demo 不能做：

- 生成完整行程。
- 调用高德地图或和风天气。
- 查询酒店、航班、火车票。
- 做长期记忆或自动评估。

## 后续演进

- `src/travel_agent/`：逐步加入 LLM Provider、schemas、tools、agents、memory、eval 等模块。
- `configs/`：保存配置模板，真实密钥只通过环境变量提供。
- `data/`：保存 mock 数据、RAG 知识库和评估任务集。
- `evals/`：保存评估规则和 runner。
- `app/`：后期提供 FastAPI / Web UI 服务。

## 当前课程锚点

- Lesson 00 对应 `src/travel_agent/schemas.py`。
- Lesson 01 对应 `src/travel_agent/clarification.py`。
- Lesson 02 对应 `src/travel_agent/llm_provider.py`。
- Lesson 03 对应 `src/travel_agent/map_tools.py`。

课程代码会从基础封装开始逐步变成最终实现；测试优先覆盖不需要外部 API 的本地行为。

教学文本位于 `../course/`，项目说明位于 `../project_docs/`。
