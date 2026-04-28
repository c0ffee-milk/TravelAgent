# 技术栈规划

本文档定义 TravelAgent 教学项目的默认技术栈和引入顺序。

## 默认技术栈

| 层级 | 默认选择 | 说明 |
| --- | --- | --- |
| 语言 | Python 3.10+ | Agent 生态成熟，适合教学 |
| 大模型 | DeepSeek | 国内模型优先，按 OpenAI-compatible API 使用 |
| LLM 接口 | OpenAI-compatible Chat Completions | 降低后续切换模型服务方的成本 |
| 地图/POI | 高德地图 API | 地理编码、地点搜索、路线规划 |
| 天气 | 和风天气 API | 实况天气、天气预报、风险提示 |
| 评估 | pytest + JSONL task set | 先规则评估，后续加入 LLM-as-judge |
| Agent 编排 | 原生 Python -> LangGraph | 先理解循环和状态，再引入图式工作流 |
| 服务化 | FastAPI | 后期提供 HTTP API |
| 前端 | 后期再定 | 当前只预留 Web UI 目录 |

## 引入顺序

1. Python 标准库和基础项目结构。
2. DeepSeek LLM Provider。
3. 结构化输出和 schema。
4. 高德地图、和风天气工具。
5. ReAct / Planning 原生实现。
6. LangGraph 工作流。
7. RAG、向量检索和记忆。
8. 多智能体协作。
9. FastAPI 服务化和观测。

## 不在第一阶段引入

- 不引入真实酒店/航班交易 API。
- 不引入数据库迁移。
- 不引入复杂前端框架。
- 不引入自动部署流水线。
- 不实现任何具体 lesson 代码。

## Provider 规划

默认模型配置：

```text
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

实现阶段应通过统一 Provider 接口封装模型调用，避免 lesson 代码直接绑定具体 SDK。

