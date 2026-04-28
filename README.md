# TravelAgent

一个围绕“旅游规划业务”构建的 Agent 教学项目。

项目目标不是一次性写出复杂 Agent，而是围绕同一个真实业务，从需求澄清、工具调用、规划、检索、记忆、多智能体协作、评估到生产化，逐步学习 Agent 系统的构建方法。

当前仓库采用三层结构，明确分离项目说明、教学文本和完整 Agent 实现：

- `project_docs/`：项目说明文档，包含架构、技术栈、业务场景、数据/API 前置条件和参考项目调研。
- `course/`：教学文本，每节课是一个直接面向学习者的 Markdown 指导书。
- `agent/`：未来完整可独立运行的 Agent 项目，目前只保留工程骨架，不包含业务实现。

## 项目定位

TravelAgent 采用“业务主线 + 技术递进”的组织方式：

- 业务主线：用户提出旅行需求，系统完成需求澄清、目的地研究、行程规划、预算估算、酒店/交通推荐、风险提示和最终方案生成。
- 技术主线：Prompt -> Tool Use -> ReAct -> Planning -> RAG/Memory -> Multi-Agent -> Protocols -> Evaluation -> Production。
- 教学主线：每一章先解释要解决的业务痛点，再引入必要 Agent 技术，最后生成对应课案与代码。

默认技术选择：

- 语言与工程：Python 优先。
- 大模型服务：DeepSeek，按 OpenAI-compatible API 方式规划。
- 真实数据源：高德地图 + 和风天气。
- 酒店、航班、火车票：第一阶段只设计 Tool Contract，不接入真实交易 API。
- 服务形态：早期 CLI 教学，后期预留 FastAPI/Web。

## 目录结构

```text
TravelAgent/
  README.md
  project_docs/     # 项目说明文档
  course/           # 教学文本
  agent/            # 可独立运行 Agent 项目骨架
```

`course/` 与 `agent/` 分离：课程文档讲“为什么”和“怎么搭”，`agent/` 承载最终可运行工程。每节课都应该是对 `agent/` 项目的增量搭建或修改。

## 文档导航

架构与前置条件：

- [project_docs/architecture.md](project_docs/architecture.md)：总体系统架构。
- [project_docs/tech-stack.md](project_docs/tech-stack.md)：技术栈和引入顺序。
- [project_docs/business-scenarios.md](project_docs/business-scenarios.md)：旅游规划业务场景。
- [project_docs/data-and-apis.md](project_docs/data-and-apis.md)：数据来源、API 服务方和环境变量。
- [project_docs/course-roadmap.md](project_docs/course-roadmap.md)：课程路线。
- [project_docs/project-structure.md](project_docs/project-structure.md)：目录规范。

参考调研：

- [project_docs/00-reference-projects.md](project_docs/00-reference-projects.md)：6 个开源项目覆盖的知识点、组织方式和可借鉴设计。
- [project_docs/01-learning-path.md](project_docs/01-learning-path.md)：早期学习路径草案。
- [project_docs/02-business-case.md](project_docs/02-business-case.md)：早期业务拆解草案。
- [project_docs/03-project-organization.md](project_docs/03-project-organization.md)：早期项目组织草案。

课程与工程：

- [course/README.md](course/README.md)：课程目录和 lesson 生成规则。
- [agent/README.md](agent/README.md)：Agent 工程骨架说明。

## 当前仓库边界

当前阶段已开始生成教学文本，但 `agent/` 仍只保留空骨架和规范，不包含：

- Agent 业务实现代码。
- 真实 API 调用代码。
- 自动评估 runner。
- Web/API 服务实现。

## 后续生成规则

当开始学习某一章时，再按需创建或完善 `course/lesson_xx_topic_name.md`。每个 lesson 默认说明：

- 本节基础知识。
- 本节要实现或修改的 `agent/` 模块。
- 推荐搭建步骤。
- 关键设计取舍。
- 自检标准。

lesson 必须沿同一个旅游规划业务逐步升级，不能变成互不相关 demo。课程文本不保存完整代码；完整实现逐步沉淀到 `agent/`。
