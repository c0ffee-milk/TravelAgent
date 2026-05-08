"""TravelAgent 的高德地图工具。

本文件对应第 03 课：地图工具。

地图工具只负责查询地图事实：
- 地点在哪里
- 有哪些 POI
- 两点之间大概多远、多久
- 高德 API 返回了什么

它不负责生成旅游推荐文案，也不负责最终行程规划。
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, parse, request

DEFAULT_AMAP_BASE_URL = "https://restapi.amap.com"

class AmapConfigurationError(RuntimeError):
    """高德地图配置错误，例如缺少 AMAP_API_KEY。"""


class AmapToolError(RuntimeError):
    """高德地图工具调用或响应解析错误。"""

class UrlOpen(Protocol):
    """可替换的 urlopen 函数类型，便于后续测试时注入 fake urlopen。"""

    def __call__(self, url: request.Request, *, timeout: float) -> Any:
        ...

@dataclass(frozen=True)
class AmapConfig:
    """高德地图 API 配置，包含 API 密钥和可选的 API 基础 URL。"""

    api_key: str
    base_url: str = DEFAULT_AMAP_BASE_URL
    timeout_seconds: float = 60

    @classmethod
    def from_env(cls) -> "AmapConfig":
        api_key = os.getenv("AMAP_API_KEY", "").strip()
        base_url = os.getenv("AMAP_BASE_URL", DEFAULT_AMAP_BASE_URL).strip()
        timeout_seconds = parse_float_env("AMAP_TIMEOUT_SECONDS", default=60.0)

        if not api_key:
            raise AmapConfigurationError("缺少环境变量 AMAP_API_KEY。")
        if not base_url:
            raise AmapConfigurationError("环境变量 AMAP_BASE_URL 不能为空。")
        if timeout_seconds <= 0:
            raise AmapConfigurationError("环境变量 AMAP_TIMEOUT_SECONDS 必须大于 0。")

        return cls(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout_seconds=timeout_seconds,
        )

@dataclass(frozen=True)
class Coordinate:
    """高德坐标。

    高德 Web 服务使用 “经度,纬度” 格式。
    """

    longitude: float
    latitude: float

    @classmethod
    def from_amap_location(cls, location: str) -> "Coordinate":
        parts = [part.strip() for part in location.split(",")]
        if len(parts) != 2:
            raise AmapToolError(f"高德坐标格式错误：{location}")

        try:
            longitude = float(parts[0])
            latitude = float(parts[1])
        except ValueError as exc:
            raise AmapToolError(f"高德坐标格式错误：{location}") from exc

        return cls(longitude=longitude, latitude=latitude)

    def to_amap_location(self) -> str:
        return f"{self.longitude},{self.latitude}"

@dataclass(frozen=True)
class GeocodeResult:
    """高德地图地理编码结果。"""

    formatted_address: str
    province: str | None
    city: str | None
    district: str | None
    adcode: str | None
    location: Coordinate
    level: str | None
    raw: dict[str, Any]

@dataclass(frozen=True)
class AmapPOI:
    """高德地图 POI 信息。"""
    
    poi_id: str | None
    name: str
    poi_type: str | None
    address: str | None
    city: str | None
    location: Coordinate | None
    distance: int | None
    raw: dict[str, Any]

@dataclass(frozen=True)
class RouteResult:
    """路线规划结果。"""

    origin: Coordinate
    destination: Coordinate
    mode: str
    distance_meters: int | None
    duration_seconds: int | None
    summary: str | None
    steps: list[str]
    raw: dict[str, Any]

class AmapClient:
    """高德地图 Web 服务客户端。

    这一层只负责地图事实查询，不写旅游推荐理由。
    """

    def __init__(self, config: AmapConfig, urlopen: UrlOpen | None = None) -> None:
        self.config = config
        self._urlopen = urlopen or request.urlopen

    def geocode(self, address: str, city: str | None = None) -> GeocodeResult:
        """把地址或地点名称转换为坐标。"""

        params = {
            "address": address,
        }
        if city:
            params["city"] = city

        data = self._get("/v3/geocode/geo", params)
        geocodes = data.get("geocodes")
        if not isinstance(geocodes, list) or not geocodes:
            raise AmapToolError(f"未找到地理编码结果：{address}")

        item = geocodes[0]
        if not isinstance(item, dict):
            raise AmapToolError("高德 geocodes[0] 不是对象。")

        location_text = as_optional_string(item.get("location"))
        if not location_text:
            raise AmapToolError("高德地理编码结果缺少 location。")

        return GeocodeResult(
            formatted_address=as_string(item.get("formatted_address")),
            province=as_optional_string(item.get("province")),
            city=normalize_amap_text(item.get("city")),
            district=normalize_amap_text(item.get("district")),
            adcode=as_optional_string(item.get("adcode")),
            location=Coordinate.from_amap_location(location_text),
            level=as_optional_string(item.get("level")),
            raw=item,
        )

    def search_poi(
        self,
        keyword: str,
        city: str | None = None,
        types: str | None = None,
        page: int = 1,
        offset: int = 10,
    ) -> list[AmapPOI]:
        """根据关键词搜索 POI。"""

        if page < 1:
            raise AmapToolError("page 必须大于等于 1。")
        if offset < 1 or offset > 25:
            raise AmapToolError("offset 建议在 1 到 25 之间。")

        params: dict[str, Any] = {
            "keywords": keyword,
            "page": page,
            "offset": offset,
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types

        data = self._get("/v3/place/text", params)
        pois = data.get("pois")
        if not isinstance(pois, list):
            raise AmapToolError("高德 POI 响应缺少 pois 数组。")

        return [parse_poi(item) for item in pois if isinstance(item, dict)]

    def walking_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
    ) -> RouteResult:
        """步行路线规划。"""

        data = self._get(
            "/v3/direction/walking",
            {
                "origin": origin.to_amap_location(),
                "destination": destination.to_amap_location(),
            },
        )
        return parse_route_result(
            data=data,
            origin=origin,
            destination=destination,
            mode="walking",
        )
    
    def driving_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        strategy: int | None = None,
    ) -> RouteResult:
        """驾车路线规划。"""

        params: dict[str, Any] = {
            "origin": origin.to_amap_location(),
            "destination": destination.to_amap_location(),
        }
        if strategy is not None:
            params["strategy"] = strategy
        
        data = self._get("/v3/direction/driving", params)
        return parse_route_result(
            data=data,
            origin=origin,
            destination=destination,
            mode="driving",
        )
    
    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 GET 请求并检查高德通用响应。"""

        url = self._build_url(path, params)
        http_request = request.Request(url, method="GET")

        try:
            with self._urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AmapToolError(f"高德 HTTP 请求失败：{exc.code} {detail}") from exc
        except (error.URLError, TimeoutError, socket.timeout) as exc:
            reason = getattr(exc, "reason", exc)
            raise AmapToolError(f"高德网络请求失败：{reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AmapToolError("高德响应不是合法 JSON。") from exc

        if not isinstance(data, dict):
            raise AmapToolError("高德响应必须是 JSON 对象。")

        status = str(data.get("status", ""))
        if status != "1":
            info = data.get("info")
            infocode = data.get("infocode")
            raise AmapToolError(f"高德 API 返回失败：status={status}, info={info}, infocode={infocode}")

        return data

    def _build_url(self, path: str, params: dict[str, Any]) -> str:
        query = {
            **params,
            "key": self.config.api_key,
            "output": "json",
        }
        encoded_query = parse.urlencode(query, doseq=True)
        return f"{self.config.base_url}{path}?{encoded_query}"

def parse_poi(item: dict[str, Any]) -> AmapPOI:
    """解析单个 POI。"""

    location = None
    location_text = as_optional_string(item.get("location"))
    if location_text:
        location = Coordinate.from_amap_location(location_text)

    return AmapPOI(
        poi_id=as_optional_string(item.get("id")),
        name=as_string(item.get("name")),
        poi_type=as_optional_string(item.get("type")),
        address=normalize_amap_text(item.get("address")),
        city=normalize_amap_text(item.get("cityname")),
        location=location,
        distance=as_optional_int(item.get("distance")),
        raw=item,
    )

def parse_route_result(
    data: dict[str, Any],
    origin: Coordinate,
    destination: Coordinate,
    mode: str,
) -> RouteResult:
    """解析步行或驾车路线结果。"""

    route = data.get("route")
    if not isinstance(route, dict):
        raise AmapToolError("高德路线响应缺少 route 对象。")

    paths = route.get("paths")
    if not isinstance(paths, list) or not paths:
        raise AmapToolError("高德路线响应缺少 paths。")

    path = paths[0]
    if not isinstance(path, dict):
        raise AmapToolError("高德路线 paths[0] 不是对象。")

    steps = parse_route_steps(path.get("steps"))

    return RouteResult(
        origin=origin,
        destination=destination,
        mode=mode,
        distance_meters=as_optional_int(path.get("distance")),
        duration_seconds=as_optional_int(path.get("duration")),
        summary=as_optional_string(path.get("strategy")) or build_route_summary(steps),
        steps=steps,
        raw=path,
    )

def parse_route_steps(value: Any) -> list[str]:
    """解析路线步骤文本。"""

    if not isinstance(value, list):
        return []

    steps = []
    for item in value:
        if not isinstance(item, dict):
            continue

        instruction = as_optional_string(item.get("instruction"))
        road = as_optional_string(item.get("road"))
        distance = as_optional_string(item.get("distance"))

        parts = []
        if instruction:
            parts.append(instruction)
        if road:
            parts.append(f"道路：{road}")
        if distance:
            parts.append(f"距离：{distance}米")

        if parts:
            steps.append("；".join(parts))

    return steps

def build_route_summary(steps: list[str]) -> str | None:
    """从路线步骤生成简短摘要。"""

    if not steps:
        return None
    return " -> ".join(steps[:3])

def parse_float_env(name: str, default: float) -> float:
    """读取 float 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise AmapConfigurationError(f"环境变量 {name} 必须是数字。") from exc


def as_string(value: Any) -> str:
    """把值转换为必填字符串。"""

    text = as_optional_string(value)
    if text is None:
        raise AmapToolError("高德响应缺少必填字符串字段。")
    return text

def as_optional_string(value: Any) -> str | None:
    """把值转换为可选字符串。"""

    if value is None:
        return None
    if isinstance(value, list):
        return None
    if isinstance(value, dict):
        return None

    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "[]"}:
        return None
    return text


def normalize_amap_text(value: Any) -> str | None:
    """清理高德响应中可能出现的空数组或空字符串。"""

    return as_optional_string(value)

def as_optional_int(value: Any) -> int | None:
    """把值转换为可选整数。"""

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

    try:
        return int(float(text))
    except ValueError:
        return None
