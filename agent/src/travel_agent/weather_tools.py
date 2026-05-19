"""TravelAgent 的和风天气工具。

本文件对应第 04 课：天气工具。

天气工具只负责查询和解释天气事实：
- 目的地对应哪个和风 Location ID
- 未来几天的天气预报是什么
- 天气对旅行有什么显性风险

它不负责生成完整行程，也不直接决定景点取舍。
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import gzip
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol
from urllib import error, parse, request

from .schemas import TravelRequest


DEFAULT_QWEATHER_BASE_URL = "https://devapi.qweather.com"

class QWeatherConfigurationError(RuntimeError):
    """和风天气配置错误，例如缺少 QWEATHER_API_KEY。"""


class QWeatherToolError(RuntimeError):
    """和风天气工具调用或响应解析错误。"""


class UrlOpen(Protocol):
    """可替换的 urlopen 函数类型，便于后续测试时注入 fake urlopen。"""

    def __call__(self, url: request.Request, *, timeout: float) -> Any:
        ...

@dataclass(frozen=True)
class QWeatherConfig:
    """和风天气 API 配置。"""

    api_key: str
    base_url: str = DEFAULT_QWEATHER_BASE_URL
    timeout_seconds: float = 30.0
    max_retries: int = 2
    auth_mode: str = "auto"

    @classmethod
    def from_env(cls) -> "QWeatherConfig":
        api_key = os.getenv("QWEATHER_API_KEY", "").strip()
        base_url = normalize_qweather_base_url(
            os.getenv("QWEATHER_BASE_URL", DEFAULT_QWEATHER_BASE_URL)
        )
        timeout_seconds = parse_float_env("QWEATHER_TIMEOUT_SECONDS", default=30.0)
        max_retries = parse_int_env("QWEATHER_MAX_RETRIES", default=2)
        auth_mode = os.getenv("QWEATHER_AUTH_MODE", "auto").strip().lower()

        if not api_key:
            raise QWeatherConfigurationError("缺少环境变量 QWEATHER_API_KEY。")
        if not base_url:
            raise QWeatherConfigurationError("环境变量 QWEATHER_BASE_URL 不能为空。")
        if timeout_seconds <= 0:
            raise QWeatherConfigurationError("环境变量 QWEATHER_TIMEOUT_SECONDS 必须大于 0。")
        if max_retries < 0:
            raise QWeatherConfigurationError("环境变量 QWEATHER_MAX_RETRIES 不能小于 0。")
        if auth_mode not in {"auto", "bearer", "header_key", "query_key"}:
            raise QWeatherConfigurationError(
                "环境变量 QWEATHER_AUTH_MODE 只能是 auto、bearer、header_key 或 query_key。"
            )

        if auth_mode == "auto":
            auth_mode = infer_auth_mode(api_key)

        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            auth_mode=auth_mode,
        )


@dataclass(frozen=True)
class WeatherLocation:
    """和风天气地点查询结果。"""

    location_id: str
    name: str
    adm1: str | None
    adm2: str | None
    country: str | None
    latitude: float | None
    longitude: float | None
    timezone: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class DailyWeather:
    """单日天气预报。"""

    forecast_date: str
    text_day: str | None
    text_night: str | None
    temp_max: int | None
    temp_min: int | None
    wind_dir_day: str | None
    wind_scale_day: str | None
    wind_speed_day: int | None
    humidity: int | None
    precip: float | None
    uv_index: int | None
    visibility_km: int | None
    raw: dict[str, Any]

@dataclass(frozen=True)
class WeatherForecast:
    """天气预报结果。"""

    location: WeatherLocation
    update_time: str | None
    fx_link: str | None
    daily: list[DailyWeather]
    raw: dict[str, Any]

@dataclass(frozen=True)
class WeatherRisk:
    """天气风险提示。"""

    level: str
    title: str
    message: str
    affected_dates: list[str] = field(default_factory=list)

class QWeatherClient:
    """和风天气 Web API 客户端。"""

    def __init__(self, config: QWeatherConfig, urlopen: UrlOpen | None = None) -> None:
        self.config = config
        self._urlopen = urlopen or request.urlopen

    def lookup_city(
            self,
            location: str,
            adm: str | None = None,
            range_country: str | None = "cn",
            number: int = 3,
            lang: str = "zh"
    ) -> list[WeatherLocation]:
        """查询城市或地区，返回可用于天气 API 的 Location ID。"""

        params: dict[str, Any] = {
            "location": location,
            "number": number,
            "lang": lang,
        }
        if adm:
            params["adm"] = adm
        if range_country:
            params["range"] = range_country

        data = self._get("/geo/v2/city/lookup", params)
        locations = data.get("location")
        if not isinstance(locations, list) or not locations:
            raise QWeatherToolError(f"未找到匹配的地点：{location}，行政区：{adm}。")
        
        return [parse_weather_location(item) for item in locations if isinstance(item, dict)]
        
    def daily_forecast(
        self,
        location: WeatherLocation,
        days: str = "7d",
        lang: str = "zh",
        unit: str = "m",
    ) -> WeatherForecast:
        """查询逐日天气预报。"""

        if days not in {"3d", "7d", "10d", "15d", "30d"}:
            raise QWeatherToolError("days 必须是 3d、7d、10d、15d 或 30d。")
        
        data = self._get(
            f"/v7/weather/{days}",
            {
                "location": location.location_id,
                "lang": lang,
                "unit": unit
            }
        )

        daily_data = data.get("daily")
        if not isinstance(daily_data, list):
            raise QWeatherToolError(f"天气预报响应缺少 daily 字段或格式错误。")
        
        return WeatherForecast(
                location=location,
                update_time=as_optional_string(data.get("updateTime")),
                fx_link=as_optional_string(data.get("fxLink")),
                daily=[parse_daily_weather(item) for item in daily_data if isinstance(item, dict)],
                raw=data,
            )
    
    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = self._build_url(path, params)
        headers = self._build_headers()

        http_request = request.Request(url, headers=headers, method="GET")
        body = self._send_with_retries(http_request)

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise QWeatherToolError("和风天气响应不是合法 JSON。") from exc

        if not isinstance(data, dict):
            raise QWeatherToolError("和风天气响应必须是 JSON 对象。")

        code = str(data.get("code", ""))
        if code != "200":
            raise QWeatherToolError(f"和风天气 API 返回失败：code={code}")

        return data

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept-Encoding": "gzip",
        }
        if self.config.auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.auth_mode == "header_key":
            headers["X-QW-Api-Key"] = self.config.api_key
        return headers
    
    def _send_with_retries(self, http_request: request.Request) -> str:
        last_error: BaseException | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                with self._urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                    return decode_response_body(
                        response.read(),
                        response.headers.get("Content-Encoding"),
                    )
            except error.HTTPError as exc:
                detail = decode_response_body(
                    exc.read(),
                    exc.headers.get("Content-Encoding"),
                    errors="replace",
                )
                raise QWeatherToolError(f"和风天气 HTTP 请求失败：{exc.code} {detail}") from exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    reason = getattr(exc, "reason", exc)
                    raise QWeatherToolError(f"和风天气网络请求失败：{reason}") from exc
                time.sleep(min(2**attempt, 4))

        raise QWeatherToolError(f"和风天气网络请求失败：{last_error}") from last_error
    
    def _build_url(self, path: str, params: dict[str, Any]) -> str:
        query = dict(params)
        if self.config.auth_mode == "query_key":
            query["key"] = self.config.api_key

        encoded_query = parse.urlencode(query, doseq=True)
        return f"{self.config.base_url}{path}?{encoded_query}"
    
def build_weather_preview_lines_for_request(travel_request: TravelRequest) -> list[str]:
    """根据完整旅行请求生成天气事实预览。"""

    return build_weather_preview_lines(
        destination=travel_request.destination,
        date_range=travel_request.date_range,
        trip_days=travel_request.days,
    )

def build_weather_preview_lines(
    destination: str | None,
    date_range: str | None = None,
    trip_days: int | None = None,
) -> list[str]:
    """生成适合 CLI 展示的轻量天气预览。"""

    if not destination:
        return ["天气预览：当前还没有明确目的地，跳过天气查询。"]

    try:
        config = QWeatherConfig.from_env()
    except QWeatherConfigurationError:
        return ["天气预览：未检测到 QWEATHER_API_KEY，跳过天气查询。"]

    if not is_short_term_forecast_applicable(date_range):
        return [
            "天气预览：当前出行时间不在短期天气预报窗口内。",
            "- 天气工具将在临近出行时查询实时预报；当前只记录目的地天气风险需要后续复查。",
        ]

    try:
        client = QWeatherClient(config)
        location = client.lookup_city(destination, number=1)[0]
        forecast = client.daily_forecast(
            location,
            days=choose_forecast_days(trip_days),
        )
    except QWeatherToolError as exc:
        return [f"天气预览：查询天气时发生错误，跳过天气展示。错误详情：{exc}"]
    
    risks = analyze_weather_risks(forecast.daily)

    lines = [
        "天气预览：",
        f"- 天气地点：{format_weather_location(forecast.location)}",
    ]
    if forecast.update_time:
        lines.append(f"- 预报更新时间：{forecast.update_time}")

    for item in forecast.daily[: min(3, len(forecast.daily))]:
        lines.append(f"- {format_daily_weather(item)}")
    
    if risks:
        lines.append("- 天气风险提示：")
        for risk in risks[:3]:
            dates = f"（{', '.join(risk.affected_dates)}）" if risk.affected_dates else ""
            lines.append(f"  - [{risk.level}] {risk.title}{dates}：{risk.message}")
    else:
        lines.append("- 天气风险：短期预报未发现明显高温、低温、强降水或大风风险。")

    return lines
    
def parse_weather_location(item: dict[str, Any]) -> WeatherLocation:
    """解析和风 GeoAPI 的地点结果。"""

    return WeatherLocation(
        location_id=as_string(item.get("id"), "和风地点缺少 id。"),
        name=as_string(item.get("name"), "和风地点缺少 name。"),
        adm1=as_optional_string(item.get("adm1")),
        adm2=as_optional_string(item.get("adm2")),
        country=as_optional_string(item.get("country")),
        latitude=as_optional_float(item.get("lat")),
        longitude=as_optional_float(item.get("lon")),
        timezone=as_optional_string(item.get("tz")),
        raw=item,
    )

def parse_daily_weather(item: dict[str, Any]) -> DailyWeather:
    """解析和风逐日天气结果。"""

    return DailyWeather(
        forecast_date=as_string(item.get("fxDate"), "和风逐日天气缺少 fxDate。"),
        text_day=as_optional_string(item.get("textDay")),
        text_night=as_optional_string(item.get("textNight")),
        temp_max=as_optional_int(item.get("tempMax")),
        temp_min=as_optional_int(item.get("tempMin")),
        wind_dir_day=as_optional_string(item.get("windDirDay")),
        wind_scale_day=as_optional_string(item.get("windScaleDay")),
        wind_speed_day=as_optional_int(item.get("windSpeedDay")),
        humidity=as_optional_int(item.get("humidity")),
        precip=as_optional_float(item.get("precip")),
        uv_index=as_optional_int(item.get("uvIndex")),
        visibility_km=as_optional_int(item.get("vis")),
        raw=item,
    )

def analyze_weather_risks(daily_items: list[DailyWeather]) -> list[WeatherRisk]:
    """把天气预报转换成旅行风险提示。"""

    risks: list[WeatherRisk] = []

    rain_dates = [
        item.forecast_date
        for item in daily_items
        if has_precipitation_risk(item)
    ]
    if rain_dates:
        risks.append(
            WeatherRisk(
                level="medium",
                title="降水影响",
                message="建议准备雨具，并为户外景点预留室内备选方案。",
                affected_dates=rain_dates,
            )
        )

    hot_dates = [
        item.forecast_date
        for item in daily_items
        if item.temp_max is not None and item.temp_max >= 35
    ]
    if hot_dates:
        risks.append(
            WeatherRisk(
                level="high",
                title="高温风险",
                message="减少正午户外活动，优先安排早晚游览和室内休息。",
                affected_dates=hot_dates,
            )
        )

    cold_dates = [
        item.forecast_date
        for item in daily_items
        if item.temp_min is not None and item.temp_min <= 0
    ]
    if cold_dates:
        risks.append(
            WeatherRisk(
                level="medium",
                title="低温风险",
                message="需要补充保暖衣物，避免把清晨和夜间活动排得过满。",
                affected_dates=cold_dates,
            )
        )

    wind_dates = [
        item.forecast_date
        for item in daily_items
        if max_wind_scale(item.wind_scale_day) >= 6
    ]
    if wind_dates:
        risks.append(
            WeatherRisk(
                level="medium",
                title="大风风险",
                message="高处、湖边、海边和缆车类活动需要谨慎安排。",
                affected_dates=wind_dates,
            )
        )

    uv_dates = [
        item.forecast_date
        for item in daily_items
        if item.uv_index is not None and item.uv_index >= 8
    ]
    if uv_dates:
        risks.append(
            WeatherRisk(
                level="low",
                title="强紫外线",
                message="建议准备防晒用品，长时间户外活动需要补水和遮阳。",
                affected_dates=uv_dates,
            )
        )

    return risks


def has_precipitation_risk(item: DailyWeather) -> bool:
    """判断是否存在降水风险。"""

    text = " ".join(value for value in [item.text_day, item.text_night] if value)
    if any(keyword in text for keyword in ["雨", "雪", "雷", "冰雹"]):
        return True
    return item.precip is not None and item.precip >= 10


def max_wind_scale(value: str | None) -> int:
    """从风力字符串中提取最大风力等级。"""

    if value is None:
        return 0
    numbers = [int(match) for match in re.findall(r"\d+", value)]
    return max(numbers) if numbers else 0

def choose_forecast_days(trip_days: int | None) -> str:
    """根据旅行天数选择天气预报窗口。"""

    if trip_days is None or trip_days <= 3:
        return "3d"
    if trip_days <= 7:
        return "7d"
    if trip_days <= 10:
        return "10d"
    if trip_days <= 15:
        return "15d"
    return "30d"

def is_short_term_forecast_applicable(date_range: str | None) -> bool:
    """判断是否适合调用短期天气预报。

    和风逐日天气预报是面向近期的 API。
    若用户明确说的是明年或更远年份，这里不调用真实预报，
    避免把当前天气误当作未来旅行天气。
    """

    if not date_range:
        return True

    current_year = date.today().year
    years = [int(match) for match in re.findall(r"\d{4}", date_range)]
    if years and all(year != current_year for year in years):
        return False
    if any(keyword in date_range for keyword in ["明年", "后年", "春节", "五一", "国庆"]):
        return False
    return True

def format_weather_location(location: WeatherLocation) -> str:
    """格式化天气地点。"""

    parts = [location.name]
    for value in [location.adm2, location.adm1, location.country]:
        if value and value not in parts:
            parts.append(value)
    return " / ".join(parts)


def format_daily_weather(item: DailyWeather) -> str:
    """格式化单日天气摘要。"""

    temp = "未知温度"
    if item.temp_min is not None and item.temp_max is not None:
        temp = f"{item.temp_min}-{item.temp_max}℃"

    weather_text = item.text_day or "未知天气"
    if item.text_night and item.text_night != item.text_day:
        weather_text = f"{weather_text}转{item.text_night}"

    extras = []
    if item.wind_dir_day and item.wind_scale_day:
        extras.append(f"{item.wind_dir_day}{item.wind_scale_day}级")
    if item.precip is not None:
        extras.append(f"降水量{item.precip:g}mm")
    if item.uv_index is not None:
        extras.append(f"紫外线{item.uv_index}")

    suffix = f"；{'，'.join(extras)}" if extras else ""
    return f"{item.forecast_date}：{weather_text}，{temp}{suffix}"


def parse_float_env(name: str, default: float) -> float:
    """读取 float 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise QWeatherConfigurationError(f"环境变量 {name} 必须是数字。") from exc


def parse_int_env(name: str, default: int) -> int:
    """读取 int 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise QWeatherConfigurationError(f"环境变量 {name} 必须是整数。") from exc


def infer_auth_mode(api_key: str) -> str:
    """根据凭据形态推断和风天气认证模式。

    JWT 通常是 header.payload.signature 三段式；普通 API KEY 默认走
    X-QW-Api-Key 请求头。用户仍可通过 QWEATHER_AUTH_MODE 显式覆盖。
    """

    if api_key.count(".") == 2:
        return "bearer"
    return "header_key"


def normalize_qweather_base_url(value: str) -> str:
    """归一化和风天气 API Host。

    和风控制台展示的 API Host 有时是不带协议的纯域名。
    urllib 需要完整 URL，所以这里自动补全 https://。
    """

    base_url = value.strip().rstrip("/")
    if not base_url:
        return ""
    if "://" not in base_url:
        base_url = f"https://{base_url}"
    return base_url


def decode_response_body(
    body: bytes,
    content_encoding: str | None,
    errors: str = "strict",
) -> str:
    """解码和风天气响应体，兼容默认 gzip 压缩。"""

    encoding = (content_encoding or "").lower()
    if "gzip" in encoding or body.startswith(b"\x1f\x8b"):
        body = gzip.decompress(body)
    return body.decode("utf-8", errors=errors)


def as_string(value: Any, error_message: str) -> str:
    """把值转换为必填字符串。"""

    text = as_optional_string(value)
    if text is None:
        raise QWeatherToolError(error_message)
    return text


def as_optional_string(value: Any) -> str | None:
    """把值转换为可选字符串。"""

    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return None

    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "[]"}:
        return None
    return text


def as_optional_int(value: Any) -> int | None:
    """把值转换为可选整数。"""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        return int(float(text))
    except ValueError:
        return None


def as_optional_float(value: Any) -> float | None:
    """把值转换为可选浮点数。"""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None
