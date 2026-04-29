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

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).strip()
        model = os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()

        if not api_key:
            raise LLMConfigurationError("缺少环境变量 DEEPSEEK_API_KEY。")
        if not base_url:
            raise LLMConfigurationError("环境变量 DEEPSEEK_BASE_URL 不能为空。")
        if not model:
            raise LLMConfigurationError("环境变量 DEEPSEEK_MODEL 不能为空。")

        return cls(api_key=api_key, base_url=base_url.rstrip("/"), model=model)

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

        try:
            with self._urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMProviderError(f"LLM HTTP 请求失败：{exc.code} {detail}") from exc
        except error.URLError as exc:
            raise LLMProviderError(f"LLM 网络请求失败：{exc.reason}") from exc

        return parse_chat_completion_response(response_body)

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

def build_travel_request_extraction_messages(raw_query: str) -> list[LLMMessage]:
    system_prompt = (
        "你是旅游规划 Agent 的需求理解模块。"
        "请只根据用户原文抽取字段，不要编造用户没有提供的信息。"
        "如果字段缺失，请使用 null 或空数组。"
        "输出必须是一个 JSON 对象。"
    )
    user_prompt = f"""
    请从下面的旅行需求中抽取 TravelRequest 草案。

    需要输出字段：
    - destination
    - origin
    - date_range
    - days
    - travelers
    - budget
    - budget_scope
    - pace
    - themes
    - constraints

    用户需求：
    {raw_query}
    """
    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]
