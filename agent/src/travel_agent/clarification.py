"""TravelAgent 需求澄清模块。

本文件对应第 01 课：需求澄清。

目标：
- 承载 LLM 驱动的自然澄清结果。
- 同时保留用户事实、归一化字段、业务理解、假设、风险和下一步动作。
- 在进入规划前执行少量 Agent 层 ready 守门规则。
- 为后续工具调用、行程规划和评估模块提供稳定输入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import TravelRequest


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

    if needs_transport_preference_check(request):
        return build_transport_preference_question(request)

    if request.pace is None and not request.themes:
        destination = request.destination or "这次旅行"
        return f"确认一下旅行风格：你这次去{destination}更偏经典景点打卡、城市漫游美食，还是轻松休闲为主？"

    return None


def needs_transport_preference_check(request: TravelRequest) -> bool:
    if not request.origin or not request.destination:
        return False
    return (
        request.long_distance_transport_preference is None
        or request.local_transport_preference is None
    )


def build_transport_preference_question(request: TravelRequest) -> str:
    origin = request.origin or "出发地"
    destination = request.destination or "目的地"
    return (
        f"进入规划前我还想确认一下交通偏好：{origin}到{destination}这类大交通你更偏高铁、飞机、自驾，还是都可以？"
        f"到{destination}后当地交通更偏公共交通、打车、步行为主，还是无所谓？"
    )


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
