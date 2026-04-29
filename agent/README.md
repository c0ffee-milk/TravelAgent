# TravelAgent Agent Project

本目录是未来完整可独立运行的旅游规划 Agent 工程根目录。

当前状态：保留工程骨架和少量注释型模块，不包含完整业务实现、真实 API 调用、运行脚本或 Web 服务。

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
  tests/
    test_llm_provider.py
  data/
    README.md
    mock/
    knowledge_base/
    eval/
  evals/
    README.md
  scripts/
    README.md
  app/
    README.md
```

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

课程代码会从基础封装开始逐步变成最终实现；测试优先覆盖不需要外部 API 的本地行为。

教学文本位于 `../course/`，项目说明位于 `../project_docs/`。
