"""TravelAgent 需求澄清模块。

本文件对应第 01 课：需求澄清。

目标：
- 判断 TravelRequest 中哪些关键信息已经明确。
- 找出缺失字段。
- 根据优先级生成少量澄清问题。
- 明确区分“事实”和“假设”。
- 为后续 LLM Provider、工具调用和规划模块提供稳定输入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import BudgetScope, TravelRequest


@dataclass
class ClarificationResult:
    """一次需求澄清的结果。"""

    known_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    ready_for_planning: bool = False


@dataclass
class ConversationState:
    """多轮澄清过程中需要维护的状态。"""

    request: TravelRequest
    asked_questions: list[str] = field(default_factory=list)
    user_answers: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    ready_for_planning: bool = False


@dataclass
class NaturalNextAction:
    """LLM 驱动澄清中的下一步动作。"""

    action_type: str = "ask"
    question: str | None = None
    reason: str | None = None


@dataclass
class NaturalClarificationResult:
    """LLM 驱动的自然澄清结果。

    它不只保存槽位，还保存模型对旅行场景的业务理解。
    """

    facts: dict[str, Any] = field(default_factory=dict)
    normalized: dict[str, Any] = field(default_factory=dict)
    inferred: dict[str, Any] = field(default_factory=dict)
    missing_decisions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_action: NaturalNextAction = field(default_factory=NaturalNextAction)
    ready_for_planning: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def natural_clarification_from_dict(data: dict[str, Any]) -> NaturalClarificationResult:
    """把 LLM 输出转换为自然澄清结果。

    LLM 输出不可信，所以这里做轻量类型兜底，避免 demo 因为字段类型漂移直接崩溃。
    """

    next_action_data = data.get("next_action")
    if not isinstance(next_action_data, dict):
        next_action_data = {}

    return NaturalClarificationResult(
        facts=as_dict(data.get("facts")),
        normalized=as_dict(data.get("normalized")),
        inferred=as_dict(data.get("inferred")),
        missing_decisions=as_string_list(data.get("missing_decisions")),
        assumptions=as_string_list(data.get("assumptions")),
        risks=as_string_list(data.get("risks")),
        next_action=NaturalNextAction(
            action_type=as_optional_string(next_action_data.get("type")) or "ask",
            question=as_optional_string(next_action_data.get("question")),
            reason=as_optional_string(next_action_data.get("reason")),
        ),
        ready_for_planning=bool(data.get("ready_for_planning")),
        raw=data,
    )


def apply_natural_ready_guard(
    result: NaturalClarificationResult,
    request: TravelRequest,
) -> NaturalClarificationResult:
    """在自然澄清结果进入规划前，应用 Agent 层 ready 守门规则。

    只有当 LLM 已经认为可以进入规划时，才应用守门规则。
    如果 LLM 本轮仍在正常追问，Agent 不应该覆盖它的 next_action。
    """

    if not result.ready_for_planning and result.next_action.action_type != "ready":
        return result

    guard_question = build_natural_ready_guard_question(request, result)
    if guard_question is None:
        return result

    result.ready_for_planning = False
    result.next_action = NaturalNextAction(
        action_type="ask",
        question=guard_question,
        reason="Agent ready guard 要求进入规划前先确认关键旅行决策。",
    )
    return result


def build_natural_ready_guard_question(
    request: TravelRequest,
    result: NaturalClarificationResult,
) -> str | None:
    """生成进入规划前必须补问的问题。"""

    if needs_companion_constraint_check(request, result):
        return "同行人里有父母、老人或孩子时，我需要确认一下体力和照顾需求。有没有步行强度、饮食、住宿或交通方面需要特别注意的地方？"

    if request.pace is None and not request.themes:
        destination = request.destination or "这次旅行"
        return f"确认一下旅行风格：你这次去{destination}更偏经典景点打卡、城市漫游美食，还是轻松休闲为主？"

    return None


def needs_companion_constraint_check(
    request: TravelRequest,
    result: NaturalClarificationResult,
) -> bool:
    """判断是否因为特殊同行人而必须先确认约束。"""

    if request.constraints:
        return False

    text = " ".join(
        [
            request.raw_query or "",
            str(request.travelers or ""),
            stringify_context(result.facts),
            stringify_context(result.inferred),
        ]
    )
    sensitive_companion_keywords = [
        "父母",
        "老人",
        "孩子",
        "儿童",
        "亲子",
        "孕妇",
        "family_with_parents",
        "with_parents",
        "elderly",
        "children",
    ]
    return any(keyword in text for keyword in sensitive_companion_keywords)


def stringify_context(value: Any) -> str:
    """把上下文对象压成字符串，便于做轻量关键词判断。"""

    if isinstance(value, dict):
        return " ".join(f"{key} {stringify_context(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(stringify_context(item) for item in value)
    if value is None:
        return ""
    return str(value)


def as_dict(value: Any) -> dict[str, Any]:
    """把 LLM 输出字段安全转换为 dict。"""

    return value if isinstance(value, dict) else {}


def as_string_list(value: Any) -> list[str]:
    """把 LLM 输出字段安全转换为字符串列表。"""

    if value is None:
        return []
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip() and not isinstance(item, (dict, list))
        ]
    text = str(value).strip()
    return [text] if text else []


def as_optional_string(value: Any) -> str | None:
    """把 LLM 输出字段安全转换为可选字符串。"""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


REQUIRED_FIELDS = [
    "destination",
    "origin",
    "date_range",
    "days",
    "travelers",
]

IMPORTANT_FIELDS = [
    "budget",
    "budget_scope",
    "pace",
    "constraints",
]

QUESTION_TEMPLATES = {
    "destination": "你这次更想去哪个目的地？如果还没确定，可以告诉我偏好的地区或旅行主题。",
    "origin": "你从哪个城市出发？这会影响交通时间和预算估算。",
    "date_range": "你大概哪几天出行？如果日期还没定，可以先告诉我月份或大致时间段。",
    "days": "这次旅行计划安排几天？",
    "travelers": "这次一共几位出行？同行人之间是什么关系，比如情侣、亲子、朋友或带父母？",
    "budget": "这次旅行总预算大概是多少？",
    "budget_scope": "这个预算是否包含往返大交通和酒店？",
    "pace": "你希望行程节奏偏轻松、适中，还是紧凑多打卡？",
    "constraints": "有没有必须考虑的限制，比如签证、老人孩子体力、饮食禁忌或不能接受的交通方式？",
}


FIELD_PRIORITY = {
    "origin": 100,
    "date_range": 95,
    "destination": 90,
    "days": 85,
    "travelers": 80,
    "budget": 70,
    "budget_scope": 65,
    "constraints": 60,
    "pace": 50,
}


def clarify_request(request: TravelRequest, max_questions: int = 3) -> ClarificationResult:
    """对一次旅行需求做澄清分析。

    这是 Lesson 01 的核心入口函数。

    参数：
    - request：已经从用户输入中初步整理出的 TravelRequest。
    - max_questions：本轮最多追问几个问题，默认最多 3 个。

    返回：
    - ClarificationResult：包含已知字段、缺失字段、澄清问题、假设和是否可进入规划。
    """

    known_fields = get_known_fields(request)
    missing_fields = get_missing_fields(request)
    assumptions = build_assumptions(request, missing_fields)
    questions = build_clarifying_questions(
        missing_fields=missing_fields,
        request=request,
        max_questions=max_questions,
    )

    ready_for_planning = is_ready_for_planning(request, missing_fields)

    request.missing_fields = missing_fields
    request.assumptions.extend(
        assumption for assumption in assumptions if assumption not in request.assumptions
    )

    return ClarificationResult(
        known_fields=known_fields,
        missing_fields=missing_fields,
        questions=questions,
        assumptions=assumptions,
        ready_for_planning=ready_for_planning,
    )


def get_known_fields(request: TravelRequest) -> list[str]:
    """返回当前已经明确的字段。"""

    known_fields = []

    if request.destination:
        known_fields.append("destination")
    if request.origin:
        known_fields.append("origin")
    if request.date_range:
        known_fields.append("date_range")
    if request.days:
        known_fields.append("days")
    if request.travelers:
        known_fields.append("travelers")
    if request.budget is not None:
        known_fields.append("budget")
    if request.budget_scope != BudgetScope.UNKNOWN:
        known_fields.append("budget_scope")
    if request.pace:
        known_fields.append("pace")
    if request.themes:
        known_fields.append("themes")
    if request.constraints:
        known_fields.append("constraints")

    return known_fields


def get_missing_fields(request: TravelRequest) -> list[str]:
    """返回当前缺失字段。

    注意：
    - 必填字段缺失时，一定进入 missing_fields。
    - 重要字段缺失时，不一定阻塞规划，但会影响方案质量。
    """

    missing_fields = []

    if not request.destination:
        missing_fields.append("destination")
    if not request.origin:
        missing_fields.append("origin")
    if not request.date_range:
        missing_fields.append("date_range")
    if not request.days:
        missing_fields.append("days")
    if not request.travelers:
        missing_fields.append("travelers")

    if request.budget is None:
        missing_fields.append("budget")
    if request.budget_scope == BudgetScope.UNKNOWN:
        missing_fields.append("budget_scope")
    if request.pace is None:
        missing_fields.append("pace")

    if not request.constraints:
        missing_fields.append("constraints")

    return sort_fields_by_priority(missing_fields)


def build_clarifying_questions(
    missing_fields: list[str],
    request: TravelRequest,
    max_questions: int = 3,
) -> list[str]:
    """根据缺失字段生成澄清问题。

    规则：
    - 一轮最多问 max_questions 个问题。
    - 优先问会影响交通、预算、安全和目的地范围的问题。
    - 已经能合理假设的问题可以暂时不问。
    """

    question_fields = []

    for field_name in missing_fields:
        if should_ask_now(field_name, request):
            question_fields.append(field_name)

    question_fields = sort_fields_by_priority(question_fields)
    question_fields = question_fields[:max_questions]

    return [QUESTION_TEMPLATES[field_name] for field_name in question_fields]


def should_ask_now(field_name: str, request: TravelRequest) -> bool:
    """判断某个缺失字段是否应该本轮追问。"""

    if field_name in REQUIRED_FIELDS:
        return True

    if field_name == "budget":
        return True

    if field_name == "budget_scope" and request.budget is not None:
        return True

    if field_name == "constraints":
        # 后续课程改为由 LLM 结合完整上下文判断当前是否需要追问 constraints。
        # 当前版本先沿用关键词启发式规则。
        return has_sensitive_travel_context(request)

    if field_name == "pace":
        return False

    return False


def build_assumptions(request: TravelRequest, missing_fields: list[str]) -> list[str]:
    """根据缺失字段生成显式假设。

    假设不是事实。后续生成方案时，必须把这些假设展示给用户。
    """

    assumptions = []

    if "pace" in missing_fields:
        assumptions.append("未说明旅行节奏，暂按适中节奏规划。")

    if not request.themes:
        assumptions.append("未说明旅行主题，暂按首次到访的经典路线规划。")

    if "constraints" in missing_fields and not has_sensitive_travel_context(request):
        assumptions.append("未说明特殊限制，暂按无明显饮食、体力和交通禁忌处理。")

    return assumptions


def is_ready_for_planning(request: TravelRequest, missing_fields: list[str]) -> bool:
    """判断当前需求是否已经可以进入初版规划。

    进入初版规划不代表信息完美，只代表已经有足够信息生成一个带假设的草案。
    """

    blocking_fields = {
        "destination",
        "origin",
        "date_range",
        "days",
        "travelers",
    }

    if any(field_name in missing_fields for field_name in blocking_fields):
        return False

    if request.budget is None:
        return False

    if request.budget_scope == BudgetScope.UNKNOWN:
        return False

    return True


def update_conversation_state(
    state: ConversationState,
    user_answer: str,
    updated_request: TravelRequest,
) -> ConversationState:
    """根据用户新回答更新对话状态。

    当前版本不负责从自然语言中抽取字段。
    后续 Lesson 02 接入 LLM Provider 后，可以把 user_answer 解析成 updated_request。
    """

    state.user_answers.append(user_answer)
    state.request = updated_request

    result = clarify_request(updated_request)
    state.assumptions = result.assumptions
    state.ready_for_planning = result.ready_for_planning

    for question in result.questions:
        if question not in state.asked_questions:
            state.asked_questions.append(question)

    return state


def sort_fields_by_priority(fields: list[str]) -> list[str]:
    """按澄清优先级排序字段。"""

    return sorted(fields, key=lambda field_name: FIELD_PRIORITY.get(field_name, 0), reverse=True)


def has_sensitive_travel_context(request: TravelRequest) -> bool:
    """判断是否存在更需要追问安全/约束信息的上下文。"""

    text_parts = [
        request.raw_query,
        request.travelers or "",
        " ".join(request.themes),
        " ".join(request.constraints),
    ]
    text = " ".join(text_parts)

    sensitive_keywords = [
        "孩子",
        "儿童",
        "亲子",
        "父母",
        "老人",
        "孕妇",
        "安全",
        "高原",
        "雪山",
        "徒步",
        "自驾",
        "过敏",
        "签证",
    ]

    return any(keyword in text for keyword in sensitive_keywords)
