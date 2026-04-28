# 课程路线

课程文本放在 `course/` 下，每节课直接对应一个 Markdown 指导书。完整 Agent 实现逐步沉淀到 `agent/`。

| Lesson | 主题 | 业务能力 | Agent 技术 | 产物边界 |
| --- | --- | --- | --- | --- |
| 00 | 项目启动与业务建模 | 理解旅游规划业务对象和端到端流程 | Agent 基础概念、结构化思维 | 课案、业务 schema 讲解 |
| 01 | 需求澄清 | 追问日期、预算、人数、偏好、约束 | 槽位抽取、对话状态 | 多轮澄清 lesson |
| 02 | LLM Provider | 接入 DeepSeek 生成结构化草案 | OpenAI-compatible API、环境变量 | LLM 封装 lesson |
| 03 | 地图工具 | 查询地点、POI、路线 | Tool calling、参数 schema | 高德工具 lesson |
| 04 | 天气工具 | 用天气影响行程选择 | 外部 API、风险提示 | 和风天气 lesson |
| 05 | ReAct Agent | 动态决定下一步查什么 | Thought/Action/Observation | ReAct 循环 lesson |
| 06 | 规划型 Agent | 分解复杂旅行规划任务 | Plan-and-Execute | 任务计划 lesson |
| 07 | RAG 知识库 | 检索攻略和目的地资料 | Embedding、检索增强 | 目的地知识库 lesson |
| 08 | 用户记忆 | 复用长期偏好 | 短期/长期记忆 | 用户画像 lesson |
| 09 | 多智能体协作 | 研究员、规划师、预算员、审稿员协作 | Multi-Agent | 协作编排 lesson |
| 10 | 评估与观测 | 判断方案是否满足约束 | Eval、trace、回归测试 | 评估 lesson |
| 11 | 服务化 | 提供 API/Web 入口 | FastAPI、配置、安全 | 服务化 lesson |

## 每个 lesson 的标准产物

后续生成具体 lesson 时，默认创建或更新：

- `course/lesson_xx_topic_name.md`：面向学习者的搭建指导书。
- `agent/` 中对应模块：添加或更新注释、TODO、接口边界或实现。

## 课程约束

- 每个 lesson 必须服务同一个旅游规划业务。
- 每个 lesson 只能引入当前阶段必要的技术。
- 每个 lesson 都应该说明它对 `agent/` 的增量影响。
- 后续 lesson 可以使用 mock fallback，但架构按真实 API 优先设计。
