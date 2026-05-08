# Lesson 01：LLM 驱动的自然需求澄清

本节重新定义 TravelAgent 的需求澄清方式：不要把对话做成“固定字段表单”，而是让 Agent 维护一个自然的旅行理解状态。用户说的是旅行意图，Agent 要理解的是事实、隐含场景、缺失决策、风险和下一步最自然的问题。

本节重点不是接 API，而是设计澄清状态和对话策略。Lesson 02 再用 DeepSeek 生成这个状态。

## 本节目标

完成本节后，你应该能够：

- 区分“槽位缺失”和“决策缺失”。
- 理解为什么真实旅游 Agent 不能只按固定字段追问。
- 设计 `NaturalClarificationResult` 这类自然澄清状态。
- 判断下一轮应该问哪个最有价值的问题。
- 删除表单式追问函数，让需求澄清主线统一为 LLM 驱动的自然澄清。

## 核心变化

旧方案：

```text
抽取 TravelRequest -> 统计缺失字段 -> 按固定优先级问字段
```

新方案：

```text
多轮对话 -> LLM 生成自然澄清状态 -> Agent 问一个最关键的问题
```

自然澄清状态包含：

- `facts`：用户原话中的事实。
- `normalized`：归一化后的 `TravelRequest` 字段。
- `inferred`：业务理解，例如父母同行、预算类型、目的地粒度。
- `missing_decisions`：还缺哪些会影响规划质量的决策。
- `assumptions`：当前显式假设。
- `risks`：已经能看出的规划风险。
- `next_action`：下一步问什么，或是否 ready。
- `ready_for_planning`：是否可以进入初版规划。

## 为什么更自然

用户说：

```text
我明年3月份想去上海旅游，跟我父母一起，人均5000。
```

表单式 Agent 会继续问：

```text
这个预算是否包含往返大交通和酒店？
```

自然澄清 Agent 应该意识到：

- 父母同行会影响步行强度。
- 上海一周行程要考虑住宿位置和交通便利度。
- 人均 5000 需要换算总预算。

更好的追问是：

```text
带父母出行的话，我需要先确认他们的体力和步行接受度。你们希望整体轻松一点，还是可以接受每天多走一些？
```

这不是字段更完整，而是对旅行场景更敏感。

## 本节要修改的 Agent 模块

本节对应：

- `agent/src/travel_agent/clarification.py`

本节新增或升级：

- `NaturalNextAction`
- `NaturalClarificationResult`
- `natural_clarification_from_dict()`

旧的 `clarify_request()`、`ClarificationResult`、`ConversationState` 不再保留。它们属于表单式槽位追问路线，已经被自然澄清状态替代。

## 推荐搭建步骤

### Step 1：保留原始事实

不要一上来就把用户的话压成字段。

例如：

```json
{
  "facts": {
    "companions": "我和父母",
    "budget": "人均5000"
  }
}
```

这些原始表达后续很重要，因为“人均”“父母”都带有业务含义。

### Step 2：再做归一化

归一化字段服务后续计算：

```json
{
  "normalized": {
    "travelers": 3,
    "budget": 15000,
    "budget_scope": "include_transport_and_hotel"
  }
}
```

但归一化不能替代事实层。

### Step 3：显式写业务理解

例如：

```json
{
  "inferred": {
    "traveler_group": "family_with_parents",
    "budget_type": "per_person",
    "planning_focus": ["步行强度", "住宿位置"]
  }
}
```

这一步让 Agent 从“抽字段”进入“理解业务”。

### Step 4：只问一个最关键问题

每轮只问一个问题，但这个问题要自然、有理由、能改变规划分支。

示例：

```json
{
  "next_action": {
    "type": "ask",
    "question": "带父母出行的话，我需要先确认他们的体力和步行接受度。你们希望整体轻松一点，还是可以接受每天多走一些？",
    "reason": "父母同行会直接影响景点密度、交通方式和住宿位置"
  }
}
```

## 自检标准

完成本节后，你应该能回答：

- 为什么旧的字段缺失列表不等于 `missing_decisions`？
- 为什么 `facts` 和 `normalized` 要同时保留？
- 父母、儿童、孕妇、老人同行为什么会改变追问优先级？
- 什么时候可以进入规划？
- 为什么本项目后续不再维护表单式追问函数？
