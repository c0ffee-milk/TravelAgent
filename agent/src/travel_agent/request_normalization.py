"""TravelRequest 归一化与多轮合并。"""

from __future__ import annotations

import re
from typing import Any

from .schemas import BudgetScope, TimePrecision, TravelPace, TravelRequest


def travel_request_from_dict(data: dict[str, Any], raw_query: str) -> TravelRequest:
    """把模型 JSON 转成项目内部 TravelRequest。"""

    date_range = as_optional_string(data.get("date_range"))
    return TravelRequest(
        raw_query=raw_query,
        destination=as_optional_string(data.get("destination")),
        origin=as_optional_string(data.get("origin")),
        date_range=date_range,
        time_precision=derive_time_precision(date_range),
        days=as_optional_int(data.get("days")),
        travelers=as_optional_string(data.get("travelers")),
        budget=as_optional_int(data.get("budget")),
        budget_scope=normalize_budget_scope(data.get("budget_scope")),
        long_distance_transport_preference=as_optional_string(
            data.get("long_distance_transport_preference")
        ),
        local_transport_preference=as_optional_string(
            data.get("local_transport_preference")
        ),
        pace=normalize_travel_pace(data.get("pace")),
        themes=as_string_list(data.get("themes")),
        constraints=as_string_list(data.get("constraints")),
    )


def merge_travel_request(
    previous: TravelRequest | None,
    current: TravelRequest,
) -> TravelRequest:
    """合并上一轮已确认字段，避免 LLM 在下一轮抽取时把旧信息丢掉。"""

    if previous is None:
        return current

    date_range = choose_better_date_range(previous.date_range, current.date_range)
    return TravelRequest(
        raw_query=previous.raw_query,
        destination=choose_better_destination(previous.destination, current.destination),
        origin=current.origin or previous.origin,
        date_range=date_range,
        time_precision=choose_better_time_precision(
            previous.time_precision,
            derive_time_precision(date_range),
        ),
        days=current.days if current.days is not None else previous.days,
        travelers=current.travelers or previous.travelers,
        budget=current.budget if current.budget is not None else previous.budget,
        budget_scope=(
            current.budget_scope
            if current.budget_scope != BudgetScope.UNKNOWN
            else previous.budget_scope
        ),
        long_distance_transport_preference=(
            current.long_distance_transport_preference
            or previous.long_distance_transport_preference
        ),
        local_transport_preference=(
            current.local_transport_preference or previous.local_transport_preference
        ),
        pace=current.pace or previous.pace,
        themes=current.themes or previous.themes,
        constraints=current.constraints or previous.constraints,
        assumptions=previous.assumptions,
    )


def choose_better_date_range(previous: str | None, current: str | None) -> str | None:
    if previous is None:
        return current
    if current is None:
        return previous

    previous_score = score_date_range(previous)
    current_score = score_date_range(current)
    if current_score >= previous_score:
        return current
    return previous


def choose_better_destination(previous: str | None, current: str | None) -> str | None:
    """合并目的地时保留更具体的表达。

    LLM 在多轮对话后有时会把“西藏拉萨周边”重新输出成“西藏”。
    对旅行规划来说，后者是信息降级，所以这里用轻量启发式保留更具体的目的地。
    """

    if previous is None:
        return current
    if current is None:
        return previous
    if previous == current:
        return current

    previous_score = score_destination_specificity(previous)
    current_score = score_destination_specificity(current)
    if current_score >= previous_score:
        return current
    return previous


def score_destination_specificity(value: str) -> int:
    """估算目的地表达的具体程度。"""

    text = value.strip()
    if not text:
        return 0

    score = len(text)
    specific_markers = [
        "周边",
        "附近",
        "市区",
        "城区",
        "古城",
        "景区",
        "路线",
        "大环线",
        "小环线",
    ]
    broad_markers = [
        "亚洲",
        "欧洲",
        "东南亚",
        "中国",
        "西藏",
        "新疆",
        "云南",
        "四川",
    ]

    for marker in specific_markers:
        if marker in text:
            score += 20
    for separator in ["、", ",", "，", "/", "\\", "和"]:
        if separator in text:
            score += 8
    if any(marker == text for marker in broad_markers):
        score -= 15

    return score


def score_date_range(value: str) -> int:
    score = 0
    if re.search(r"\d{4}", value):
        score += 4
    if "年" in value:
        score += 2
    if "月" in value:
        score += 2
    if re.search(r"\d{4}年\d{1,2}月\d{1,2}(?:日|号)?", value):
        score += 4
    if re.search(r"\d{1,2}[/-]\d{1,2}", value):
        score += 2
    if any(relative_word in value for relative_word in ["下个月", "明年", "五一"]):
        score += 1
    return score


def derive_time_precision(
    date_range: str | None,
    raw_time: str | None = None,
) -> TimePrecision:
    text = " ".join(value for value in [date_range, raw_time] if value)
    if not text:
        return TimePrecision.UNKNOWN

    has_day = bool(
        re.search(r"\d{4}年\d{1,2}月\d{1,2}(?:日|号)?", text)
        or re.search(r"\d{1,2}[/-]\d{1,2}", text)
    )
    if has_day:
        return TimePrecision.DAY

    has_range = any(marker in text for marker in ["至", "到", "-", "—", "~", "～", "之间"])
    if has_range:
        return TimePrecision.RANGE

    if re.search(r"\d{4}年\d{1,2}月", text):
        return TimePrecision.MONTH
    if re.search(r"\d{4}年", text):
        return TimePrecision.YEAR
    return TimePrecision.UNKNOWN


def choose_better_time_precision(
    previous: TimePrecision,
    current: TimePrecision,
) -> TimePrecision:
    if time_precision_rank(current) >= time_precision_rank(previous):
        return current
    return previous


def time_precision_rank(value: TimePrecision) -> int:
    return {
        TimePrecision.UNKNOWN: 0,
        TimePrecision.YEAR: 1,
        TimePrecision.MONTH: 2,
        TimePrecision.RANGE: 3,
        TimePrecision.DAY: 4,
    }[value]


def normalize_travel_pace(value: Any) -> TravelPace | None:
    text = as_optional_string(value)
    if text is None:
        return None

    lowered = text.lower()
    if lowered in {"relaxed", "轻松", "慢", "慢节奏", "休闲"}:
        return TravelPace.RELAXED
    if lowered in {"balanced", "适中", "中等", "正常"}:
        return TravelPace.BALANCED
    if lowered in {"compact", "紧凑", "赶", "多打卡"}:
        return TravelPace.COMPACT
    return None


def normalize_budget_scope(value: Any) -> BudgetScope:
    text = as_optional_string(value)
    if text is None:
        return BudgetScope.UNKNOWN

    lowered = text.lower()
    if lowered in {"local_only", "当地", "不含大交通", "只含当地"}:
        return BudgetScope.LOCAL_ONLY
    if lowered in {"include_transport", "含交通", "包含往返交通", "包含大交通"}:
        return BudgetScope.INCLUDE_TRANSPORT
    if lowered in {
        "include_transport_and_hotel",
        "含交通和酒店",
        "包含往返交通和酒店",
        "全包",
    }:
        return BudgetScope.INCLUDE_TRANSPORT_AND_HOTEL
    return BudgetScope.UNKNOWN


def as_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "unknown", "未说明"}:
        return None
    return text


def as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    normalized_text = text.replace("，", ",").replace("－", "-").replace("—", "-")
    number_groups = re.findall(r"\d+(?:\.\d+)?", normalized_text)
    if not number_groups:
        return None

    number = max(float(number_group) for number_group in number_groups)
    if "万" in normalized_text:
        number *= 10000
    elif "千" in normalized_text or "k" in normalized_text.lower():
        number *= 1000

    return int(number)


def as_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        cleaned_items = []
        for item in value:
            text = clean_optional_list_item(item)
            if text is not None:
                cleaned_items.append(text)
        return cleaned_items

    text = clean_optional_list_item(value)
    return [text] if text is not None else []


def clean_optional_list_item(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, dict):
        return None
    if isinstance(value, list):
        return None

    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none", "unknown", "n/a"}:
        return None
    if text in {"{}", "[]", "未说明", "无", "没有"}:
        return None

    return text
