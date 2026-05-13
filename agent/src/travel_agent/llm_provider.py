"""TravelAgent 的 LLM Provider 设计说明。

本文件对应第 02 课：LLM Provider。

当前先不实现具体代码，只保留模块边界和搭建注释。
你手动实现时，可以按下面的顺序逐步补齐。
"""

# 待办（第 02 课）：定义默认配置常量。
# - DEFAULT_DEEPSEEK_BASE_URL：默认值为 "https://api.deepseek.com"
# - DEFAULT_DEEPSEEK_MODEL：默认值为 "deepseek-v4-flash"

# 待办（第 02 课）：定义 LLMConfigurationError。
# 用于表示配置错误，例如缺少 DEEPSEEK_API_KEY。

# 待办（第 02 课）：定义 LLMProviderError。
# 用于表示模型调用失败、网络失败、响应格式错误或 JSON 解析失败。

# 待办（第 02 课）：定义 LLMConfig。
# 建议使用 dataclass，并包含：
# - api_key：DeepSeek API key
# - base_url：OpenAI-compatible base URL
# - model：模型名称
# - timeout_seconds：请求超时时间
# 需要提供 from_env()，从环境变量读取：
# - DEEPSEEK_API_KEY
# - DEEPSEEK_BASE_URL
# - DEEPSEEK_MODEL
# 需要提供 chat_completions_url 属性，拼出 /chat/completions 地址。

# 待办（第 02 课）：定义 LLMMessage。
# 统一表示一条模型消息：
# - role：system / user / assistant
# - content：消息内容
# 需要提供 to_api_dict()，转换成 OpenAI-compatible API 需要的字典。

# 待办（第 02 课）：定义 LLMResponse。
# 统一表示一次模型响应：
# - content：模型返回文本
# - model：响应中的模型名，可选
# - raw：原始响应对象，可选，便于后续调试和 trace

# 待办（第 02 课）：定义 DeepSeekChatClient。
# 它应该负责：
# - 接收 LLMConfig
# - 构造 HTTP POST 请求
# - 设置 Authorization: Bearer <api_key>
# - 发送到 {base_url}/chat/completions
# - 支持 temperature
# - 支持 response_format
# - 返回 LLMResponse
# 这一层不要写旅游业务逻辑，只做模型服务封装。

# 待办（第 02 课）：定义 parse_chat_completion_response(response_body)。
# 它应该解析 OpenAI-compatible Chat Completions 响应：
# - 读取 choices[0].message.content
# - 校验 content 必须是字符串
# - 返回 LLMResponse
# - 响应结构不符合预期时抛 LLMProviderError

# 待办（第 02 课）：定义 parse_json_object(content)。
# 它应该把模型输出解析成 JSON 对象：
# - JSON 解析失败时抛 LLMProviderError
# - 解析结果不是 dict 时抛 LLMProviderError
# 这个函数后续会被 TravelRequest 结构化抽取复用。

# 待办（第 02 课）：定义 build_travel_request_extraction_messages(raw_query)。
# 它应该构造两条消息：
# - system：说明模型是旅游规划 Agent 的需求理解模块，只能根据原文抽取，不要编造
# - user：要求模型从 raw_query 中抽取 TravelRequest 草案
# 输出字段建议包含：
# - destination
# - origin
# - date_range
# - days
# - travelers
# - budget
# - budget_scope
# - pace
# - themes
# - constraints

# 待办（第 02 课）：补充真实 API 连通性测试。
# 测试前需要在 shell 环境中配置真实的 DEEPSEEK_API_KEY。
# 最小测试应验证：
# - 配置读取
# - 缺少 API key 的错误
# - 请求 payload 结构
# - 真实 /chat/completions 能返回内容
# - JSON 对象解析


from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"

class LLMConfigurationError(RuntimeError):
    """LLM 配置错误，例如缺少 API key。"""


class LLMProviderError(RuntimeError):
    """LLM 调用或响应解析错误。"""

@dataclass(frozen=True)
class LLMConfig:
    """LLM Provider 配置"""

    api_key: str
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).strip()
        model = os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()
        timeout_seconds = parse_float_env("DEEPSEEK_TIMEOUT_SECONDS", default=30.0)
        max_retries = parse_int_env("DEEPSEEK_MAX_RETRIES", default=2)

        if not api_key:
            raise LLMConfigurationError("缺少环境变量 DEEPSEEK_API_KEY。")
        if not base_url:
            raise LLMConfigurationError("环境变量 DEEPSEEK_BASE_URL 不能为空。")
        if not model:
            raise LLMConfigurationError("环境变量 DEEPSEEK_MODEL 不能为空。")
        if timeout_seconds <= 0:
            raise LLMConfigurationError("环境变量 DEEPSEEK_TIMEOUT_SECONDS 必须大于 0。")
        if max_retries < 0:
            raise LLMConfigurationError("环境变量 DEEPSEEK_MAX_RETRIES 不能小于 0。")

        return cls(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

@dataclass(frozen=True)
class LLMMessage:
    """统一消息结构"""

    role: str
    content: str

    def to_api_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

@dataclass(frozen=True)
class LLMResponse:
    """统一响应结构"""

    content: str
    model: str | None = None
    raw: dict[str, Any] | None = None

class UrlOpen(Protocol):
    """可替换的 urlopen 函数类型。"""

    def __call__(self, url: request.Request, *, timeout: float) -> Any:
        ...


class DeepSeekChatClient:
    """DeepSeek Chat Completions 客户端"""

    def __init__(self, config: LLMConfig, urlopen: UrlOpen | None = None) -> None:
        self.config = config
        self._urlopen = urlopen or request.urlopen

    def chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        if not messages:
            raise LLMProviderError("messages 不能为空。")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [message.to_api_dict() for message in messages],
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        
        http_request = request.Request(
            self.config.chat_completions_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        response_body = self._send_with_retries(http_request)

        return parse_chat_completion_response(response_body)

    def _send_with_retries(self, http_request: request.Request) -> str:
        """发送请求，并对网络抖动做有限重试。"""

        last_error: BaseException | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                with self._urlopen(
                    http_request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    return response.read().decode("utf-8")
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if not is_retryable_http_error(exc.code) or attempt >= self.config.max_retries:
                    raise LLMProviderError(f"LLM HTTP 请求失败：{exc.code} {detail}") from exc
                last_error = exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt >= self.config.max_retries:
                    reason = getattr(exc, "reason", exc)
                    raise LLMProviderError(f"LLM 网络请求失败：{reason}") from exc
                last_error = exc

            time.sleep(min(2**attempt, 4))

        raise LLMProviderError(f"LLM 请求失败：{last_error}") from last_error


def parse_float_env(name: str, default: float) -> float:
    """读取 float 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise LLMConfigurationError(f"环境变量 {name} 必须是数字。") from exc


def parse_int_env(name: str, default: int) -> int:
    """读取 int 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise LLMConfigurationError(f"环境变量 {name} 必须是整数。") from exc


def is_retryable_http_error(status_code: int) -> bool:
    """判断 HTTP 错误是否适合重试。"""

    return status_code in {408, 409, 425, 429, 500, 502, 503, 504}

def parse_chat_completion_response(response_body: str) -> LLMResponse:
    try:
        data = json.loads(response_body)
        content = data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("LLM 响应格式不符合 Chat Completions 约定。") from exc

    if not isinstance(content, str):
        raise LLMProviderError("LLM 响应 content 不是字符串。")

    model = data.get("model")
    return LLMResponse(content=content, model=model if isinstance(model, str) else None, raw=data)

def parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("模型输出不是合法 JSON。") from exc

    if not isinstance(parsed, dict):
        raise LLMProviderError("模型输出必须是 JSON 对象。")

    return parsed

def build_travel_request_extraction_messages(
    raw_query: str,
    current_date: str | None = None,
    is_conversation: bool = False,
) -> list[LLMMessage]:
    """构造 TravelRequest 抽取消息。

    参数：
    - raw_query：用户原始需求，或多轮对话记录。
    - current_date：当前日期，用于理解“明年”“下个月”“五一”等相对时间。
    - is_conversation：raw_query 是否为多轮对话记录。
    """

    input_description = "多轮旅行需求对话" if is_conversation else "旅行需求"
    state_instruction = (
        "你需要从多轮对话记录中抽取最新 TravelRequest 状态。"
        if is_conversation
        else "你需要从用户原文中抽取 TravelRequest 草案。"
    )
    date_instruction = (
        f"今天的日期是 {current_date}。遇到“明年”“下个月”“五一”等相对时间时，必须以今天为基准理解。"
        if current_date
        else ""
    )
    one_shot_example = """
示例输入：
用户：想在明年五一节跟我女朋友去东南亚旅游
Agent 追问：你从哪个城市出发？这会影响交通时间和预算估算。
用户回答：武汉
Agent 追问：这次旅行计划安排几天？
用户回答：7天左右
Agent 追问：这次旅行总预算大概是多少？
用户回答：两个人总预算 12000 到 16000
Agent 追问：这个预算是否包含往返大交通和酒店？
用户回答：包含机票和酒店
Agent 追问：你希望行程节奏偏轻松、适中，还是紧凑多打卡？
用户回答：轻松一点，主要想海岛、逛夜市、吃当地美食，不想每天换城市

示例输出：
{
  "destination": "东南亚",
  "origin": "武汉",
  "date_range": "明年五一节期间",
  "days": 7,
  "travelers": 2,
  "budget": "12000 到 16000",
  "budget_scope": "include_transport_and_hotel",
  "pace": "relaxed",
  "themes": ["海岛", "夜市", "当地美食"],
  "constraints": ["不想每天换城市"]
}
"""

    system_prompt = (
        "你是旅游规划 Agent 的需求理解模块。"
        f"{state_instruction}"
        f"{date_instruction}"
        "只抽取用户明确表达过的信息，不要编造。"
        "如果字段缺失，请使用 null 或空数组。"
        "输出必须是一个 JSON 对象，不要输出 Markdown，不要解释，不要附加任何其他文本。"
    )
    user_prompt = f"""
请从下面的{input_description}中抽取 TravelRequest 草案。

字段要求：
- destination：目的地或候选目的地区域
- origin：出发城市
- date_range：出行时间；如果用户说“明年五一”，请写成“明年五一节期间”或对应年份的五一期间，不要丢失
- days：旅行天数，数字
- travelers：出行人数或同行关系
- budget：预算；如果是区间，可以原样输出区间文本
- budget_scope：预算覆盖范围，unknown / local_only / include_transport / include_transport_and_hotel
- pace：旅行节奏，relaxed / balanced / compact，无法判断则 null
- themes：旅行主题数组
- constraints：真实限制条件数组；没有就输出空数组，不要输出 {{}} 或 ["{{}}"]

请严格参考下面的 one-shot 示例格式。示例只是格式参考，不要把示例内容当作当前用户需求。

{one_shot_example}

{input_description}：
{raw_query}
"""
    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]


def build_theme_poi_query_messages(
    destination: str,
    themes: list[str],
    destination_scope: str | None = None,
) -> list[LLMMessage]:
    """为目的地和抽象主题生成适合地图检索的 POI 查询词。"""

    system_prompt = (
        "你是旅游规划 Agent 的地图检索词规划模块。"
        "你的任务是把抽象旅行主题转换成适合地图/POI 搜索的具体检索词。"
        "你必须结合目的地的真实城市语境理解主题，不要输出泛泛而谈的形容词。"
        "输出必须是严格 JSON 对象，不要 Markdown，不要解释，不要附加其他文本。"
    )
    user_prompt = f"""
请根据目的地、用户确认的目的地范围和旅行主题，输出适合地图 POI 检索的具体查询词。

目的地：{destination}
用户确认的目的地范围：{destination_scope or destination}
主题：{themes}

输出字段：
- queries: 数组，每个元素是对象，包含：
  - theme: 原始主题
  - query: 适合地图检索的具体查询词
  - reason: 为什么这个词适合在该目的地搜索

要求：
- 每个主题最多输出 2 个查询词。
- 查询词要尽量具体，可直接用于城市 POI 搜索。
- 对“城市漫游”这类抽象主题，应转成该城市更像地点/片区/体验载体的词。
- 如果用户确认的目的地范围包含“周边”“附近”“市区”等限定，查询词必须落在这个范围内。
- 不要把区域级目的地扩散到距离很远的其他城市、地区或极限路线。
- 不要输出酒店、机票、预算、攻略类词。
- 如果主题太泛，优先输出该城市中更容易检索到实体地点的词。

示例输出：
{{
  "queries": [
    {{"theme": "城市漫游", "query": "胡同", "reason": "北京 city walk 常落在胡同与历史街区"}},
    {{"theme": "城市漫游", "query": "什刹海", "reason": "北京城市漫游常见步行片区"}},
    {{"theme": "美食", "query": "美食街", "reason": "便于搜到聚合餐饮片区"}}
  ]
}}
"""
    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]


def build_natural_clarification_messages(
    transcript: str,
    current_date: str | None = None,
) -> list[LLMMessage]:
    """构造 LLM 驱动的自然澄清消息。

    这个 prompt 用于 Lesson 01/02 升级后的主流程：
    - 不再只做固定槽位抽取。
    - 同时输出事实、归一化字段、业务理解和下一步自然追问。
    """

    date_instruction = (
        f"今天的日期是 {current_date}。所有相对时间必须以今天为基准理解。"
        if current_date
        else ""
    )
    system_prompt = (
        "你是旅游规划 Agent 的需求理解与自然澄清模块。"
        f"{date_instruction}"
        "你的任务不是机械填表，而是像专业旅行顾问一样理解用户意图，"
        "判断当前最值得确认的一件事。"
        "你必须只根据对话记录抽取信息，不要编造用户没有表达过的事实。"
        "输出必须是严格 JSON 对象，不要 Markdown，不要解释，不要附加其他文本。"
    )
    one_shot = """
示例输入：
用户：我明年3月份想去上海旅游
Agent：你从哪个城市出发？这会影响交通时间和预算估算。
用户：武汉
Agent：这次大概安排几天？一个人去还是和家人朋友一起？
用户：一个周，跟我父母一起
Agent：预算大概是多少？
用户：人均5000，包含路费和住宿

示例输出：
{
  "facts": {
    "destination": "上海",
    "origin": "武汉",
    "time": "明年3月份",
    "duration": "一个周",
    "companions": "我和父母",
    "budget": "人均5000",
    "budget_scope": "包含路费和住宿"
  },
  "normalized": {
    "destination": "上海",
    "origin": "武汉",
    "date_range": "2027年3月",
    "days": 7,
    "travelers": 3,
    "budget": 15000,
    "budget_scope": "include_transport_and_hotel",
    "long_distance_transport_preference": null,
    "local_transport_preference": null,
    "pace": null,
    "themes": [],
    "constraints": []
  },
  "inferred": {
    "traveler_group": "family_with_parents",
    "budget_type": "per_person",
    "estimated_total_budget": 15000,
    "destination_granularity": "city",
    "time_precision": "month",
    "planning_focus": ["父母同行", "步行强度", "住宿位置"]
  },
  "missing_decisions": ["parents_mobility", "travel_style"],
  "assumptions": ["暂未确认父母体力和步行接受度", "暂未确认行程节奏"],
  "risks": ["父母同行时，行程过密可能影响体验"],
  "next_action": {
    "type": "ask",
    "question": "带父母出行的话，我需要先确认他们的体力和步行接受度。你们希望整体轻松一点，还是可以接受每天多走一些？",
    "reason": "父母同行会直接影响景点密度、交通方式和住宿位置"
  },
  "ready_for_planning": false
}
"""
    user_prompt = f"""
请根据下面的多轮旅行需求对话，输出一个自然澄清状态 JSON。

输出字段必须包含：
- facts：用户原话中的事实，尽量保留“人均”“跟父母”“下个月”这类原始语义。
- normalized：归一化后的 TravelRequest 字段。
- inferred：你对旅行场景的业务理解。
- missing_decisions：还缺哪些会影响规划质量的决策，不要只写字段名。
- assumptions：当前需要显式告知用户的假设。
- risks：当前已经能看出的规划风险。
- next_action：下一步动作，只允许 ask 或 ready。
- ready_for_planning：是否已经适合进入初版规划。

normalized 字段要求：
- destination：目的地或候选目的地区域。
- origin：出发城市。
- date_range：时间范围，能规范化就规范化。
- days：旅行天数，数字。
- travelers：人数，数字或可理解的同行描述。
- budget：尽量输出总预算数字；如果用户说人均预算，请结合人数估算总预算。
- budget_scope：unknown / local_only / include_transport / include_transport_and_hotel。
- long_distance_transport_preference：大交通偏好，例如高铁、飞机、自驾、都可以；无法判断则 null。
- local_transport_preference：目的地当地交通偏好，例如公共交通、打车、步行、自驾、都可以；无法判断则 null。
- pace：relaxed / balanced / compact，无法判断则 null。
- themes：旅行主题数组。
- constraints：真实限制条件数组。

下一步追问规则：
- 一次只问一个最关键、最自然的问题。
- 优先问会改变方案分支的问题，例如父母/儿童体力、目的地范围、预算含义、旅行风格。
- 不要像表单一样机械追问所有字段。
- 如果已经能规划，就把 next_action.type 设为 ready，question 设为 null。
- 如果用户带父母、老人、儿童或孕妇同行，必须优先确认体力、步行强度或特殊照顾需求。
- 如果预算是“人均”，需要在 normalized.budget 中估算总预算，并在 inferred.budget_type 标记 per_person。
- 如果目的地是“东南亚”“日本”“欧洲”这类大范围区域，通常应追问旅行风格或候选国家/城市。
- inferred.time_precision 只作为模型理解参考，不作为权威状态；时间精度由 Agent 根据 normalized.date_range 归一化。
- 如果核心旅行信息已足够，但还没有确认交通偏好，应询问一次大交通和当地交通偏好。

请严格参考 one-shot 的 JSON 结构。one-shot 只是格式示例，不要把示例内容当作当前用户需求。

{one_shot}

当前对话：
{transcript}
"""
    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]
