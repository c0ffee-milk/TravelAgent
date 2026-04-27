# 项目组织草案

本文档保留早期项目组织思路。当前正式目录规范以 [project-structure.md](project-structure.md) 为准。

## 组织原则

TravelAgent 后续采用“架构文档 + 空骨架 + 按需生成 lesson”的方式组织：

- `docs/`：放总体架构、技术栈、业务场景、数据/API、课程路线和参考项目调研。
- `lessons/`：只在用户要求生成某一课时创建具体 lesson。
- `src/travel_agent/`：只在具体 lesson 需要时逐步加入可复用代码。
- `configs/`：放环境变量和配置样例。
- `data/`：预留 mock、知识库和评估数据。
- `evals/`：预留评估规则和 runner。
- `app/`：预留后期 FastAPI/Web。
- `scripts/`：预留辅助脚本。

## Lesson 标准结构

具体 lesson 后续按需生成，默认结构为：

```text
lesson_00_topic_name/
  README.md
  lesson_plan.md
  code/
  exercises.md
  acceptance.md
```

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

