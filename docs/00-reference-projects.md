# 参考项目调研

本文档总结 6 个开源 Agent 教程/资源库的知识覆盖、组织方式，以及对 TravelAgent 教学项目的启发。

## 总体结论

这些项目可以分成四类：

| 类型 | 代表项目 | 优点 | 对 TravelAgent 的启发 |
| --- | --- | --- | --- |
| 系统教材型 | Hello-Agents、AI Agents for Beginners、Hugging Face Agents Course | 知识路径完整，适合从概念到工程逐步学习 | TravelAgent 需要有明确章节、先修要求、每章目标和验收任务 |
| 案例索引型 | 500-AI-Agents-Projects | 业务场景丰富，能帮助学习者理解 Agent 的真实落点 | TravelAgent 应以真实业务场景驱动，而不是只堆技术点 |
| 代码范例库型 | GenAI_Agents | 覆盖大量 Agent 技术形态，方便横向对比 | TravelAgent 可在每章保留最小代码样例，并逐步升级同一个业务 |
| 工程训练营型 | ed-donner/agents | 按周推进，强调环境、框架、实操和排障 | TravelAgent 要提供稳定环境说明、可运行脚本、排错指南 |

## 1. Hello-Agents

仓库：https://github.com/datawhalechina/hello-agents

### 覆盖知识点

Hello-Agents 是中文系统教程，强调从 Agent 概念、发展史、大语言模型基础，到 ReAct、Plan-and-Solve、Reflection、低代码平台、主流框架、自研框架、记忆与检索、上下文工程、通信协议、Agentic RL、评估和综合项目。

它特别适合作为 TravelAgent 的“课程骨架”参考，因为它不是只讲工具调用，而是把 Agent 当成完整系统来组织。

### 组织方式

- 分成理论基础、构建实践、高级扩展、综合案例、毕业设计。
- 每一部分由多个章节组成，章节顺序由浅入深。
- 同时提供教程正文、配套代码、社区共创内容和综合项目。

### 可借鉴点

- TravelAgent 应该先讲 Agent 基本范式，再进入框架。
- 不要一开始就把学习者锁定到某个框架，先让其理解 Agent 循环、工具、状态和评估。
- 综合案例应贯穿课程，而不是最后突然出现。

## 2. 500-AI-Agents-Projects

仓库：https://github.com/ashishpatel26/500-AI-Agents-Projects

### 覆盖知识点

该项目不是传统教程，而是 AI Agent 用例索引。它按行业、用例、框架组织大量 Agent 项目，例如医疗、金融、教育、客服、零售、法律、招聘、旅行、生产力等，并按 CrewAI、AutoGen、Agno、LangGraph 等框架分类。

### 组织方式

- 先按行业展示 Agent 能解决什么业务问题。
- 再按框架聚合用例，方便学习者选择技术栈。
- 每个用例通常包含名称、行业、描述和 GitHub 链接。

### 可借鉴点

- TravelAgent 应该把“旅行规划”拆成多个真实子场景：亲子游、商务差旅、低预算背包游、签证/风险提醒、多人偏好协调、临时改签等。
- 教程应持续回答“这个 Agent 能替真实用户解决什么问题”，避免变成纯框架演示。
- 可以在后续加入 `casebook/`，收集更多旅行类 Agent 变体。

## 3. GenAI_Agents

仓库：https://github.com/NirDiamant/GenAI_Agents

### 覆盖知识点

GenAI_Agents 是代码优先的 Agent 实现集合，覆盖从简单聊天、问答、数据分析，到 LangGraph、MCP、教育 Agent、论文 Agent、客服 Agent、旅行规划 Agent、多智能体协作、自改进 Agent、搜索 Agent、数据库 Agent、购物 Agent 等。

### 组织方式

- 以功能/场景为中心列出 Agent 实现。
- 每个实现强调可运行代码和技术特征。
- 范例覆盖多个框架，尤其适合横向比较同类能力的不同实现。

### 可借鉴点

- TravelAgent 每个阶段都应有一个“可运行 Agent”，而不是只有说明文档。
- 同一业务可以用不同架构实现：单 Agent、图式工作流、多 Agent、带检索 Agent。
- 代码目录应保持可比较：每章一个独立实现，同时共享业务数据和评估集。

## 4. Hugging Face Agents Course

仓库：https://github.com/huggingface/agents-course

### 覆盖知识点

Hugging Face Agents Course 将课程分为 4 个单元：Agent 基础、框架、Agentic RAG、最终项目与自动评估。框架部分覆盖 smolagents、LlamaIndex、LangGraph，并包含 function calling fine-tuning、观测与评估等 bonus 内容。

### 组织方式

- `units/` 目录承载课程单元。
- `quiz/` 用于学习检查。
- 课程最后有 benchmark/leaderboard 导向的 final project。

### 可借鉴点

- TravelAgent 需要设计每章 quiz/checklist，而不是只交代码。
- 最终项目要可评估：例如给定 20 个旅行需求，输出行程是否满足日期、预算、约束、风险提示和引用依据。
- 评估最好从课程中期就加入，不要等到最后。

## 5. AI Agents for Beginners

仓库：https://github.com/microsoft/ai-agents-for-beginners

### 覆盖知识点

微软课程强调初学者友好，按 lesson 组织，覆盖 Agent 介绍、框架探索、Agentic Design Patterns、工具使用、Agentic RAG、可信 Agent、规划设计、多智能体、元认知、生产化、协议、上下文工程、记忆、Microsoft Agent Framework、浏览器使用等。

### 组织方式

- 每个 lesson 是独立目录。
- 每课包含 README、短视频、Python code samples 和扩展资源。
- 提供多语言翻译、环境配置和学习指南。

### 可借鉴点

- TravelAgent 应采用 `lessons/lesson_xx_topic/README.md + code + exercises` 的结构。
- 每章都要有“学习目标、业务任务、核心概念、运行方式、练习、验收标准”。
- 生产化、可信、安全、浏览器自动化等内容应作为后半程重点。

## 6. ed-donner/agents

仓库：https://github.com/ed-donner/agents

### 覆盖知识点

该课程按 6 周推进，覆盖 OpenAI Agents SDK、CrewAI、LangGraph、AutoGen、MCP 等主流 Agent 技术，并强调真实开发环境、依赖管理、API 成本、平台差异和排障。

### 组织方式

- 按周/主题拆分目录：foundations、openai、crew、langgraph、autogen、mcp。
- 使用 notebooks 和 Python 代码混合教学。
- 有 setup、guides、troubleshooting 等工程支持内容。

### 可借鉴点

- TravelAgent 要把环境配置、成本控制、故障排查写进项目，而不是假设学习者自己解决。
- 框架教学可以采用“同一业务，多框架实现”的方式。
- 每个框架章节都应说明为什么使用它、它解决什么问题、代价是什么。

## 对 TravelAgent 的设计原则

1. 真实业务优先：旅行规划是主线，技术点服务于业务升级。
2. 同一项目递进：每章都在上一章基础上增强，而不是做彼此无关的小 demo。
3. 先原理后框架：先实现最小 Agent 循环，再引入 LangGraph、CrewAI、MCP 等框架/协议。
4. 每章可运行：每个 lesson 必须有能跑的脚本、样例输入和期望输出。
5. 每章可评估：从结构化输出、工具调用正确率、约束满足率开始，逐步加入自动评估。
6. 保留排障材料：API key、模型兼容、依赖安装、网络失败、工具超时都要有说明。
7. 最终项目导向：最终交付一个完整旅行 Agent，并用固定 benchmark 做验收。

