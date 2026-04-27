# TravelAgent 总体架构

TravelAgent 是一个教学项目，架构按“先 CLI、后服务化”的路线规划。当前阶段只定义边界和模块职责，不实现具体 lesson。

## 分层架构

```text
User
  |
  v
CLI / Future Web UI
  |
  v
Application Layer
  |
  v
Agent Core
  |
  +-- Planning
  +-- Memory
  +-- RAG
  +-- Multi-Agent Coordination
  |
  v
Tool Layer
  |
  +-- LLM Provider
  +-- Map / POI Tools
  +-- Weather Tools
  +-- Transport / Hotel Contracts
  |
  v
Data Layer
  |
  +-- External APIs
  +-- Local Knowledge Base
  +-- Mock Data
  +-- Eval Datasets
```

## 模块职责

| 模块 | 职责 | 当前状态 |
| --- | --- | --- |
| CLI | 早期课程入口，接收用户旅行需求并展示结果 | 只预留 |
| API/Web | 后期 FastAPI/Web UI，用于服务化和交互演示 | 只预留 |
| Agent Core | 承载 Agent 状态、规划、工具调用、记忆和协作 | 只规划 |
| Tool Layer | 统一封装 LLM、地图、天气、交通、酒店等外部能力 | 只规划 |
| Data Layer | 管理 mock 数据、知识库、评估集和外部 API 结果 | 只规划 |
| Eval Layer | 定义任务集、评分规则、回归比较和 trace 检查 | 只规划 |

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

- 课程开始前不实现任何 lesson。
- 业务主线始终围绕旅游规划。
- 真实 API 优先设计，但每个工具后续实现时应提供 mock fallback。
- 密钥只通过环境变量读取。
- 早期课程避免框架过载，先讲清 Agent 基本循环，再引入 LangGraph 等框架。

