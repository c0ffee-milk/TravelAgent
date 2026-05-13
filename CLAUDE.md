# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库定位

这是一个围绕“旅游规划业务”逐步教学的 Agent 项目，而不是一次性完成的生产系统。

仓库按三层拆分：
- `project_docs/`：项目背景、架构、技术栈、API 前置条件与课程路线。
- `course/`：面向学习者的 lesson 文本；每节课是一个 Markdown 文件，不再为每节课单独建目录。
- `agent/`：可独立运行的 Agent 工程；课程中的实现最终沉淀在这里。

当前重点是同一条旅游规划业务主线的渐进式演进：需求澄清 → 工具调用 → 规划 → 检索/记忆 → 多智能体 → 评估 → 服务化。

## 当前实现边界

当前仓库并不是完整旅行规划产品。

已可运行的主线是 `agent/` 下 Lesson 00–03 的早期实现，其中：
- Lesson 00：领域对象，锚点在 `agent/src/travel_agent/schemas.py`
- Lesson 01：自然澄清状态与 ready guard，锚点在 `agent/src/travel_agent/clarification.py`
- Lesson 02：DeepSeek/OpenAI-compatible LLM 封装与 prompt，锚点在 `agent/src/travel_agent/llm_provider.py`
- Lesson 03：高德地图工具层，锚点在 `agent/src/travel_agent/map_tools.py`

当前 demo 只覆盖“多轮需求澄清闭环”，不生成完整行程，也未接入天气、酒店、航班或火车票交易能力。

## 常用命令

### 运行当前 CLI demo

```bash
cd agent
python scripts/demo_clarification_chat.py
```

这个 demo 会自动尝试读取以下环境文件：
- `agent/.env`
- `agent/configs/.env`

也可以手动加载环境变量后运行：

```bash
cd agent
set -a
source .env
set +a
python scripts/demo_clarification_chat.py
```

### Python / pytest

`agent/pyproject.toml` 定义了：
- Python 版本：`>=3.10`
- pytest 的 `pythonpath = ["src"]`
- `pytest>=8.0.0` 在 optional `dev` 依赖中

仓库当前没有已提交的测试文件；如果新增测试，请在 `agent/` 目录下运行：

```bash
cd agent
python -m pytest
```

运行单个测试文件：

```bash
cd agent
python -m pytest tests/test_xxx.py
```

运行单个测试用例：

```bash
cd agent
python -m pytest tests/test_xxx.py -k test_case_name
```

### 当前未配置的内容

仓库中目前没有已验证的 lint / format 命令配置；不要在 `CLAUDE.md` 中假设存在 Ruff、Black、mypy、Makefile 或 npm 脚本。

## 关键架构理解

### 1. 顶层是“文档 / 课程 / 工程实现”三轨并行

这不是普通应用仓库；修改时要明确当前改动属于哪一层：
- 改业务说明、架构解释、技术规划：去 `project_docs/`
- 改 lesson 教学内容：去 `course/`
- 改可运行实现：去 `agent/`

`course/` 讲“为什么、学什么、按什么步骤搭”；`agent/` 承载最终代码。不要把完整实现写回课程文档里。

### 2. `agent/` 当前是一个“CLI 优先”的早期工程

`agent/scripts/demo_clarification_chat.py` 是当前真实入口。它串起的主流程是：
1. 自动加载本地 `.env`
2. 用 `LLMConfig.from_env()` 构造 DeepSeek 客户端
3. 用 `build_natural_clarification_messages(...)` 生成结构化澄清 prompt
4. 调用 `DeepSeekChatClient.chat(...)`
5. 用 `parse_json_object(...)` 与 `natural_clarification_from_dict(...)` 把模型输出转为内部状态
6. 把 `normalized` 字段转换并合并进 `TravelRequest`
7. 用 `apply_natural_ready_guard(...)` 在进入规划前补做少量 Agent 规则守门
8. 多轮循环直到 `ready_for_planning`

也就是说，当前核心不是 ReAct 或 planner，而是“LLM 驱动的自然澄清 + 少量 deterministic guard”。

### 3. 当前 `travel_agent` 包的职责边界已经初步成型

- `schemas.py`：领域对象中心，`TravelRequest` 是后续规划链路的核心输入。
- `clarification.py`：承接 LLM 澄清结果，不只存槽位，也存 `facts / normalized / inferred / missing_decisions / assumptions / risks / next_action`。
- `llm_provider.py`：统一封装模型调用、响应解析、JSON 结构化输出与澄清 prompt；不要在业务模块里散落 provider 细节。
- `map_tools.py`：只负责地图事实查询（地理编码、POI、路线），不负责生成旅行推荐文案。

未来能力应继续沿“领域对象 → LLM/工具边界 → 编排层”分离，而不是把 prompt、HTTP 调用和业务规则混在一起。

### 4. 数据源设计是“真实 API 优先，但允许 mock fallback”

`project_docs/data-and-apis.md` 明确了当前默认外部依赖：
- LLM：DeepSeek（OpenAI-compatible Chat Completions）
- 地图：高德地图 API
- 天气：和风天气 API

密钥只通过环境变量提供，配置样例见 `agent/configs/.env.example`。

文档同时要求每个真实工具后续都应支持 mock fallback，以支持无 key 学习、稳定测试和失败降级；但 mock 数据不能伪装成实时结果。

### 5. 课程与工程要保持 lesson 锚点一致

`course/README.md` 与 `agent/README.md` 约定了 lesson 到工程文件的映射。若你在推进某一课：
- 应优先修改 `agent/` 中对应锚点文件
- 仅在需要更新教学说明时再同步修改 `course/lesson_xx_*.md`
- 不要新建 `course/lesson_xx/` 目录结构

## 重要文档入口

在开始较大改动前，优先阅读：
- `README.md`：仓库整体定位
- `project_docs/architecture.md`：三层结构与演进路线
- `project_docs/tech-stack.md`：技术栈与引入顺序
- `project_docs/data-and-apis.md`：环境变量、外部 API 与 mock 策略
- `course/README.md`：lesson 组织规则
- `agent/README.md`：当前可运行边界与 lesson 锚点

## 当前工程事实

- 当前主开发目录是 `agent/`，不是仓库根目录。
- 当前可运行入口只有 `agent/scripts/demo_clarification_chat.py`。
- `agent/app/`、`agent/data/`、`agent/evals/` 目前仍主要是占位目录，后续再逐步实装。
- 仓库当前没有 repo-level `CLAUDE.md` 以外的 Cursor rules 或 Copilot instructions 可继承。
