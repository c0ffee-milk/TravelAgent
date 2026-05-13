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
- 本 demo 在信息足够时可选调用高德地图做事实预览。
- 本 demo 不调用天气、酒店或航班 API。
- 本 demo 只是把 Lesson 00-03 串起来，方便你先看到一个可对话闭环。
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path


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
from travel_agent.map_tools import build_map_preview_lines  # noqa: E402
from travel_agent.request_normalization import (  # noqa: E402
    merge_travel_request,
    travel_request_from_dict,
)
from travel_agent.schemas import BudgetScope, TravelRequest  # noqa: E402


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
            print_map_preview(request)
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


def print_map_preview(request: TravelRequest) -> None:
    """在进入规划前打印一次轻量地图事实预览。"""

    for line in build_map_preview_lines(
        destination=request.destination,
        origin=request.origin,
        themes=request.themes,
    ):
        print(line)


def print_request_snapshot(request: TravelRequest) -> None:
    """打印当前抽取到的关键信息。"""

    fields = {
        "目的地": request.destination,
        "出发地": request.origin,
        "出行时间": request.date_range,
        "时间精度": request.time_precision.value,
        "天数": request.days,
        "出行人": request.travelers,
        "预算": request.budget,
        "预算范围": (
            request.budget_scope.value
            if request.budget_scope != BudgetScope.UNKNOWN
            else None
        ),
        "大交通偏好": request.long_distance_transport_preference,
        "当地交通偏好": request.local_transport_preference,
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
            if key == "time_precision" or value in (None, [], "", {}):
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
