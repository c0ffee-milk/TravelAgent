"""TravelAgent 领域对象说明。

第 00 课使用本文件作为第一个工程锚点。
当前先不要实现完整模型，先通过下面的注释理解最终 Agent 需要哪些对象。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

class TimePrecision(str, Enum):
    """出行时间精度。"""

    UNKNOWN = "unknown"
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    RANGE = "range"


class TravelPace(str, Enum):
    """旅行节奏。"""

    RELAXED = "relaxed"
    BALANCED = "balanced"
    COMPACT = "compact"

class BudgetScope(str, Enum):
    """预算覆盖范围。"""

    UNKNOWN = "unknown"
    LOCAL_ONLY = "local_only"
    INCLUDE_TRANSPORT = "include_transport"
    INCLUDE_TRANSPORT_AND_HOTEL = "include_transport_and_hotel"

@dataclass
class TravelRequest:
    """一次旅行规划请求。

    这是 TravelAgent 最核心的输入对象。
    用户自然语言中的信息，后续会逐步被抽取并填入这个对象。
    """

    raw_query: str
    destination: str | None = None
    origin: str | None = None
    date_range: str | None = None
    time_precision: TimePrecision = TimePrecision.UNKNOWN
    days: int | None = None
    travelers: str | None = None
    budget: int | None = None
    budget_scope: BudgetScope = BudgetScope.UNKNOWN
    long_distance_transport_preference: str | None = None
    local_transport_preference: str | None = None
    pace: TravelPace | None = None
    themes: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

@dataclass
class TravelerProfile:
    """用户长期偏好。

    它不只服务本次旅行，也可以在后续课程中作为记忆模块的基础。
    """

    user_id: str | None = None
    hotel_preference: str | None = None
    food_preference: str | None = None
    walking_tolerance: str | None = None
    safety_preference: str | None = None
    language_ability: list[str] = field(default_factory=list)
    recurring_constraints: list[str] = field(default_factory=list)

@dataclass
class Destination:
    """目的地信息。

    后续可以由 RAG、地图工具、人工 mock 数据或外部 API 补充。
    """

    name: str
    country_or_region: str | None = None
    best_season: str | None = None
    budget_level: str | None = None
    transport_notes: list[str] = field(default_factory=list)
    travel_tips: list[str] = field(default_factory=list)

@dataclass
class POI:
    """兴趣点。

    POI 可以是景点、餐厅、商圈、酒店区域或交通节点。
    """

    name: str
    poi_type: str
    city: str | None = None
    address: str | None = None
    suitable_for: list[str] = field(default_factory=list)
    estimated_duration_hours: float | None = None
    notes: list[str] = field(default_factory=list)

@dataclass
class ItineraryItem:
    """单个行程活动。"""

    time_slot: str
    title: str
    location: str | None = None
    description: str | None = None
    transport: str | None = None
    estimated_cost: int | None = None
    notes: list[str] = field(default_factory=list)

@dataclass
class DayPlan:
    """一天的行程安排。"""

    day: int
    city: str | None = None
    theme: str | None = None
    items: list[ItineraryItem] = field(default_factory=list)
    daily_budget: int | None = None
    risks: list[str] = field(default_factory=list)

@dataclass
class Itinerary:
    """完整行程。"""

    title: str
    days: list[DayPlan] = field(default_factory=list)
    summary: str | None = None

@dataclass
class BudgetEstimate:
    """预算估算。"""

    total: int | None = None
    transport: int | None = None
    hotel: int | None = None
    food: int | None = None
    tickets: int | None = None
    local_transport: int | None = None
    other: int | None = None
    notes: list[str] = field(default_factory=list)

@dataclass
class RiskReport:
    """风险提示。"""

    weather_risks: list[str] = field(default_factory=list)
    transport_risks: list[str] = field(default_factory=list)
    safety_risks: list[str] = field(default_factory=list)
    visa_risks: list[str] = field(default_factory=list)
    fatigue_risks: list[str] = field(default_factory=list)
    missing_information_risks: list[str] = field(default_factory=list)

@dataclass
class TravelPlan:
    """最终旅行方案。

    后续 Agent 的目标，就是逐步生成、检查并修改这个对象。
    """

    request: TravelRequest
    itinerary: Itinerary
    budget: BudgetEstimate
    risks: RiskReport
    next_questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

@dataclass
class EvaluationResult:
    """旅行方案评估结果。

    后续评估模块会用它记录一次方案是否满足用户约束。
    """

    constraint_satisfaction: float | None = None
    factuality: float | None = None
    budget_reasonableness: float | None = None
    itinerary_feasibility: float | None = None
    risk_awareness: float | None = None
    writing_quality: float | None = None
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
