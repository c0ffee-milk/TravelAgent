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



