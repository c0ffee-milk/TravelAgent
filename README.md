# TravelAgent

一个围绕“旅游规划业务”构建的 Agent 教学项目。

项目目标不是一次性写出复杂 Agent，而是围绕同一个真实业务，从需求澄清、工具调用、规划、检索、记忆、多智能体协作、评估到生产化，逐步学习 Agent 系统的构建方法。

当前仓库处于“项目架构搭建阶段”：只规划总体架构、技术栈、业务场景、数据来源、API 服务方、课程路线和目录规范，不实现任何具体 lesson。后续开始学习时，再按需生成某一个 lesson 的课案、代码、练习和测试。

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

## 文档导航

架构与前置条件：

- [docs/architecture.md](docs/architecture.md)：总体系统架构。
- [docs/tech-stack.md](docs/tech-stack.md)：技术栈和引入顺序。
- [docs/business-scenarios.md](docs/business-scenarios.md)：旅游规划业务场景。
- [docs/data-and-apis.md](docs/data-and-apis.md)：数据来源、API 服务方和环境变量。
- [docs/course-roadmap.md](docs/course-roadmap.md)：课程路线。
- [docs/project-structure.md](docs/project-structure.md)：目录规范。

参考调研：

- [docs/00-reference-projects.md](docs/00-reference-projects.md)：6 个开源项目覆盖的知识点、组织方式和可借鉴设计。
- [docs/01-learning-path.md](docs/01-learning-path.md)：早期学习路径草案。
- [docs/02-business-case.md](docs/02-business-case.md)：早期业务拆解草案。
- [docs/03-project-organization.md](docs/03-project-organization.md)：早期项目组织草案。

## 当前仓库边界

当前阶段保留空骨架和规范，不包含：

- 可运行 lesson。
- Agent 业务实现代码。
- 真实 API 调用代码。
- 自动评估 runner。
- Web/API 服务实现。

## 后续生成规则

当开始学习某一章时，再按需创建对应 lesson。每个 lesson 独立目录，默认包含：

- `README.md`：面向学习者的课程入口。
- `lesson_plan.md`：详细课案。
- `code/`：本课代码。
- `exercises.md`：练习。
- `acceptance.md`：验收标准。

lesson 必须沿同一个旅游规划业务逐步升级，不能变成互不相关 demo。
