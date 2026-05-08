"""Lesson 00-02 可对话需求澄清 Demo。

运行方式：
    cd agent
    python scripts/demo_clarification_chat.py

这个 demo 只做三件事：
1. 调用 DeepSeek 理解多轮旅行需求。
2. 生成自然澄清状态和下一步追问。
3. 通过多轮问答逐步补齐关键决策，直到可以进入初版规划。

注意：
- 本 demo 不生成完整行程。
- 本 demo 不调用地图、天气、酒店或航班 API。
- 本 demo 只是把 Lesson 00-02 串起来，方便你先看到一个可对话闭环。
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


from travel_agent.clarification import (  # noqa: E402
    NaturalClarificationResult,
    apply_natural_ready_guard,
    natural_clarification_from_dict,
)
from travel_agent.llm_provider import (  # noqa: E402
    DeepSeekChatClient,
    LLMConfig,
    LLMConfigurationError,
    LLMProviderError,
    build_natural_clarification_messages,
    parse_json_object,
)
from travel_agent.schemas import BudgetScope, TravelPace, TravelRequest  # noqa: E402


MAX_ROUNDS = 10


def main() -> None:
    load_local_env()

    try:
        client = DeepSeekChatClient(LLMConfig.from_env())
    except LLMConfigurationError as exc:
        print(f"配置错误：{exc}")
        print("请先在 agent/.env 或 agent/configs/.env 中配置 DEEPSEEK_API_KEY。")
        return

    print("TravelAgent 需求澄清 Demo")
    print("输入一段旅行需求，我会先抽取已知信息，再追问缺失信息。")
    print("输入 exit 或 quit 可退出。")
    print()

    raw_query = input("你：").strip()
    if should_exit(raw_query):
        return
    if not raw_query:
        print("没有收到旅行需求，已退出。")
        return

    transcript = raw_query
    current_request: TravelRequest | None = None
    shown_assumptions: set[str] = set()
    shown_risks: set[str] = set()

    for round_index in range(1, MAX_ROUNDS + 1):
        print()
        print(f"--- 第 {round_index} 轮需求分析 ---")

        try:
            understanding = extract_natural_understanding(client, transcript)
        except LLMProviderError as exc:
            print(f"模型调用失败：{exc}")
            return

        request = travel_request_from_dict(understanding.normalized, raw_query)
        request = merge_travel_request(current_request, request)
        current_request = request
        understanding = apply_natural_ready_guard(understanding, request)

        print_request_snapshot(request)
        print_understanding_snapshot(understanding)

        new_assumptions = [
            assumption
            for assumption in understanding.assumptions
            if assumption not in shown_assumptions
        ]
        if new_assumptions:
            print("新增假设：")
            for assumption in new_assumptions:
                print(f"- {assumption}")
                shown_assumptions.add(assumption)

        new_risks = [risk for risk in understanding.risks if risk not in shown_risks]
        if new_risks:
            print("当前风险：")
            for risk in new_risks:
                print(f"- {risk}")
                shown_risks.add(risk)

        if understanding.ready_for_planning or understanding.next_action.action_type == "ready":
            print()
            print("当前信息已经足够进入初版规划。")
            print("下一步课程会在这个结构化请求基础上接入地图、天气和行程生成。")
            return
        else:
            question = understanding.next_action.question

        if not question:
            print()
            print("当前还有缺失决策，但模型没有生成新的追问。")
            print("你可以补充更多旅行信息后重新运行 demo。")
            return

        print()
        print(f"Agent：{question}")
        answer = input("你：").strip()

        if should_exit(answer):
            print("已退出。")
            return
        if not answer:
            print("没有收到补充信息，已退出。")
            return

        transcript += f"\n\nAgent 追问：{question}\n用户回答：{answer}"

    print()
    print("已达到最大澄清轮数。当前信息仍不完整，建议重新组织需求后再试。")


def load_local_env() -> None:
    """加载本地 .env，避免每次 demo 都手动 source。

    只在环境变量尚未存在时写入当前进程，不会修改 shell 或文件。
    """

    env_paths = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "configs" / ".env",
    ]

    for env_path in env_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def extract_natural_understanding(
    client: DeepSeekChatClient,
    transcript: str,
) -> NaturalClarificationResult:
    """用 LLM 从当前对话记录中生成自然澄清状态。"""

    response = client.chat(
        build_natural_clarification_messages(
            transcript,
            current_date=date.today().isoformat(),
        ),
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = parse_json_object(response.content)
    return natural_clarification_from_dict(data)


def merge_travel_request(
    previous: TravelRequest | None,
    current: TravelRequest,
) -> TravelRequest:
    """合并上一轮已确认字段，避免 LLM 在下一轮抽取时把旧信息丢掉。"""

    if previous is None:
        return current

    return TravelRequest(
        raw_query=previous.raw_query,
        destination=current.destination or previous.destination,
        origin=current.origin or previous.origin,
        date_range=choose_better_date_range(previous.date_range, current.date_range),
        days=current.days if current.days is not None else previous.days,
        travelers=current.travelers or previous.travelers,
        budget=current.budget if current.budget is not None else previous.budget,
        budget_scope=(
            current.budget_scope
            if current.budget_scope != BudgetScope.UNKNOWN
            else previous.budget_scope
        ),
        pace=current.pace or previous.pace,
        themes=current.themes or previous.themes,
        constraints=current.constraints or previous.constraints,
        assumptions=previous.assumptions,
        missing_fields=previous.missing_fields,
    )


def choose_better_date_range(previous: str | None, current: str | None) -> str | None:
    """合并日期字段时，优先保留更规范的日期表达。"""

    if previous is None:
        return current
    if current is None:
        return previous

    previous_score = score_date_range(previous)
    current_score = score_date_range(current)
    if current_score >= previous_score:
        return current
    return previous


def score_date_range(value: str) -> int:
    """给日期表达打分，分数越高表示越规范。"""

    score = 0
    if re.search(r"\d{4}", value):
        score += 4
    if "年" in value:
        score += 2
    if "月" in value:
        score += 2
    if re.search(r"\d{1,2}[/-]\d{1,2}", value):
        score += 2
    if any(relative_word in value for relative_word in ["下个月", "明年", "五一"]):
        score += 1
    return score


def travel_request_from_dict(data: dict[str, Any], raw_query: str) -> TravelRequest:
    """把模型 JSON 转成项目内部 TravelRequest。

    LLM 输出不可信，所有字段都需要做轻量清洗。
    """

    return TravelRequest(
        raw_query=raw_query,
        destination=as_optional_string(data.get("destination")),
        origin=as_optional_string(data.get("origin")),
        date_range=as_optional_string(data.get("date_range")),
        days=as_optional_int(data.get("days")),
        travelers=as_optional_string(data.get("travelers")),
        budget=as_optional_int(data.get("budget")),
        budget_scope=normalize_budget_scope(data.get("budget_scope")),
        pace=normalize_travel_pace(data.get("pace")),
        themes=as_string_list(data.get("themes")),
        constraints=as_string_list(data.get("constraints")),
    )


def normalize_travel_pace(value: Any) -> TravelPace | None:
    """把模型输出的旅行节奏归一化为枚举。"""

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
    """把预算覆盖范围归一化为枚举。"""

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
    """把任意值转成非空字符串。"""

    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "unknown", "未说明"}:
        return None
    return text


def as_optional_int(value: Any) -> int | None:
    """把模型输出转成整数。

    当前 TravelRequest 还没有预算区间字段。遇到“5000 到 8000”这种范围时，
    demo 先取上限作为保守预算值，避免继续卡在预算追问上。
    """

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
    """把模型输出转成字符串列表。"""

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
    """清洗模型输出列表中的单个元素。"""

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


def print_request_snapshot(request: TravelRequest) -> None:
    """打印当前抽取到的关键信息。"""

    fields = {
        "目的地": request.destination,
        "出发地": request.origin,
        "出行时间": request.date_range,
        "天数": request.days,
        "出行人": request.travelers,
        "预算": request.budget,
        "预算范围": (
            request.budget_scope.value
            if request.budget_scope != BudgetScope.UNKNOWN
            else None
        ),
        "节奏": request.pace.value if request.pace else None,
        "主题": request.themes,
        "约束": request.constraints,
    }

    print("当前已抽取信息：")
    for label, value in fields.items():
        if value in (None, [], ""):
            value = "未明确"
        print(f"- {label}: {value}")


def print_understanding_snapshot(understanding: NaturalClarificationResult) -> None:
    """打印 LLM 对当前旅行场景的业务理解。"""

    if understanding.inferred:
        print("当前业务理解：")
        for key, value in understanding.inferred.items():
            if value in (None, [], "", {}):
                continue
            print(f"- {key}: {value}")

    if understanding.missing_decisions:
        print("待确认决策：")
        for decision in understanding.missing_decisions:
            print(f"- {decision}")


def should_exit(text: str) -> bool:
    """判断用户是否希望退出。"""

    return text.strip().lower() in {"exit", "quit", "q"}


if __name__ == "__main__":
    main()
