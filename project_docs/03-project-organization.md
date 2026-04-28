# 项目组织草案

本文档保留早期项目组织思路。当前正式目录规范以 [project-structure.md](project-structure.md) 为准。

## 组织原则

TravelAgent 后续采用“架构文档 + 空骨架 + 按需生成 lesson”的方式组织：

- `project_docs/`：放总体架构、技术栈、业务场景、数据/API、课程路线和参考项目调研。
- `course/`：只在用户要求生成某一课时创建或完善具体 lesson。
- `agent/`：未来完整可独立运行的 Agent 工程。
- `agent/src/travel_agent/`：只在具体 lesson 需要时逐步加入可复用代码。
- `agent/configs/`：放环境变量和配置样例。
- `agent/data/`：预留 mock、知识库和评估数据。
- `agent/evals/`：预留评估规则和 runner。
- `agent/app/`：预留后期 FastAPI/Web。
- `agent/scripts/`：预留辅助脚本。

## Lesson 标准结构

具体 lesson 后续按需生成，默认结构为一个 Markdown 指导书：

```text
course/lesson_00_topic_name.md
```

每节课必须说明它会增量修改 `agent/` 中的哪些模块。

## 代码演进策略

正式开始 lesson 后，代码按学习曲线逐步引入：

1. 原生 Python 函数和结构化输出。
2. LLM Provider 封装。
3. Tool Layer。
4. Agent loop。
5. Planning 和状态图。
6. RAG 和 Memory。
7. Multi-Agent。
8. Eval 和服务化。

当前阶段不提前实现这些模块。
