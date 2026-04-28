# Lesson 00：项目启动与业务建模

本节课是 TravelAgent 的起点。你暂时不需要写完整功能，而是先把旅游规划 Agent 的业务边界、核心对象和工程入口搭清楚。后续每一节课都会继续修改 `agent/` 这个项目，而不是另起一个 demo。

## 本节目标

完成本节后，你应该能够：

- 说明 TravelAgent 要解决的真实业务问题。
- 区分普通聊天机器人和旅游规划 Agent。
- 识别旅游规划系统里的核心业务对象。
- 理解 `agent/` 目录为什么要作为最终可独立运行项目来维护。
- 知道后续代码应该放在哪里，而不是散落在课程文档目录中。

## 基础知识

### 1. Agent 是围绕目标工作的系统

旅游规划 Agent 不只是回答“去哪玩”。它需要围绕用户目标持续推进：

- 理解用户需求。
- 维护任务状态。
- 识别缺失信息。
- 调用外部工具。
- 生成行程方案。
- 检查预算、天气、交通和风险。
- 根据反馈调整方案。

### 2. 先建模，再写代码

在写 Agent 之前，先确定系统需要处理哪些对象。TravelAgent 的第一批对象包括：

| 对象 | 作用 |
| --- | --- |
| `TravelRequest` | 表示本次旅行需求 |
| `TravelerProfile` | 表示用户长期偏好和限制 |
| `Destination` | 表示目的地信息 |
| `POI` | 表示景点、餐厅、商圈、交通节点 |
| `Itinerary` | 表示每日行程 |
| `BudgetEstimate` | 表示预算估算 |
| `RiskReport` | 表示风险提示 |
| `EvaluationResult` | 表示方案质量评估 |

这些对象会在后续课程里逐步变成真实代码。

## 本节要修改的 Agent 模块

本节对应 `agent/` 中的增量是业务对象骨架：

- `agent/README.md`：说明 `agent/` 是最终可独立运行项目。
- `agent/src/travel_agent/README.md`：说明 Agent 核心包的职责。
- `agent/src/travel_agent/__init__.py`：标记 Python package。
- `agent/src/travel_agent/schemas.py`：用注释记录后续要实现的核心业务对象。

当前只写注释和结构，不实现具体逻辑。

## 推荐搭建步骤

### Step 1：确认项目分层

你需要记住三层目录职责：

```text
project_docs/  # 项目说明和架构文档
course/        # 每节课的学习指导书
agent/         # 最终可独立运行的 Agent 项目
```

后续所有功能代码都应该进入 `agent/`，不要写在 `course/` 里。

### Step 2：阅读 agent 骨架

重点看：

- `agent/README.md`
- `agent/src/travel_agent/README.md`
- `agent/pyproject.toml`
- `agent/configs/.env.example`

你需要确认 `agent/` 已经具备一个 Python 项目的基本形状，但还没有业务实现。

### Step 3：理解业务对象

打开 `agent/src/travel_agent/schemas.py`，先不要急着写 dataclass 或 Pydantic model。你要先读懂里面的注释：

- 哪些对象是本次旅行需求？
- 哪些对象是用户长期偏好？
- 哪些对象来自外部工具？
- 哪些对象是最终输出？
- 哪些对象用于评估？

### Step 4：手工拆解一个需求

用下面的需求练习：

```text
暑假想带 8 岁孩子和父母去云南玩 7 天，预算 18000，希望安全轻松，不要太累。
```

先手工写出：

```text
TravelRequest:
- destination:
- date_range:
- days:
- travelers:
- budget:
- pace:
- constraints:

TravelerProfile:
- family_type:
- physical_limit:
- safety_preference:

Expected output:
- itinerary:
- budget_estimate:
- risk_report:
- missing_questions:
```

## 关键设计取舍

- 不要一开始就接 LLM。先把业务对象想清楚。
- 不要把课程代码放进 `course/`。课程只是指导书。
- 不要把所有对象一次性实现完整。后续 lesson 会逐步补齐。
- `agent/` 应该始终保持可以独立成为一个 Python 项目的形状。

## 自检标准

完成本节后，你应该能回答：

- `project_docs/`、`course/`、`agent/` 分别负责什么？
- 为什么 `course/` 不保存完整 Agent 实现？
- `agent/src/travel_agent/schemas.py` 中每类业务对象解决什么问题？
- 为什么旅游规划 Agent 需要结构化对象，而不是只靠 prompt？

