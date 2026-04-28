# TravelAgent 总体架构

TravelAgent 是一个教学项目，同时也是一个逐步成长的 Agent 工程。仓库采用三层结构：

- `project_docs/`：解释项目为什么这样设计。
- `course/`：承载教学文本和 lesson。
- `agent/`：承载未来完整可独立运行的 Agent 项目。

`course/` 和 `agent/` 分离：课程负责教学组织，`agent/` 负责最终工程实现。当前阶段 `agent/` 只保留骨架，不实现业务逻辑。

## 仓库层级

```text
TravelAgent/
  project_docs/   # 项目说明
  course/         # 教学文本
  agent/          # 可独立运行的 Agent 工程
```

## Agent 工程分层

`agent/` 内部按“先 CLI、后服务化”的路线规划：

```text
agent/
  app/                 # 后期 FastAPI / Web UI
  configs/             # 环境变量和配置样例
  data/                # mock、知识库、评估数据
  evals/               # 评估规则和 runner
  scripts/             # 辅助脚本
  src/travel_agent/    # Agent 核心代码
```

未来 `src/travel_agent/` 的逻辑分层：

| 层 | 职责 |
| --- | --- |
| Application Layer | CLI、API、Web 入口 |
| Agent Core | 状态、规划、工具调用、记忆和多智能体协作 |
| Tool Layer | DeepSeek、高德地图、和风天气、交通/酒店契约 |
| Data Layer | mock 数据、知识库、评估集和外部 API 结果 |
| Eval Layer | 任务集、评分规则、trace 和回归检查 |

## 演进路线

1. CLI 单轮输入输出。
2. 多轮需求澄清。
3. 工具调用和真实 API 接入。
4. ReAct / Plan-and-Execute。
5. RAG 和用户偏好记忆。
6. 多智能体协作。
7. MCP / API 服务化。
8. 自动评估和观测。
9. Web/API 产品化。

## 架构约束

- 教学文本放在 `course/`，Agent 工程代码放在 `agent/`。
- 业务主线始终围绕旅游规划。
- 真实 API 优先设计，但每个工具后续实现时应提供 mock fallback。
- 密钥只通过环境变量读取。
- 早期课程避免框架过载，先讲清 Agent 基本循环，再引入 LangGraph 等框架。
