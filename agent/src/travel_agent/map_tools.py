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
import re
import socket
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, parse, request

from .llm_provider import (
    DeepSeekChatClient,
    LLMConfig,
    LLMConfigurationError,
    LLMProviderError,
    build_theme_poi_query_messages,
    parse_json_object,
)
from .schemas import TravelRequest

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
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AmapConfig":
        api_key = os.getenv("AMAP_API_KEY", "").strip()
        base_url = os.getenv("AMAP_BASE_URL", DEFAULT_AMAP_BASE_URL).strip()
        timeout_seconds = parse_float_env("AMAP_TIMEOUT_SECONDS", default=60.0)
        max_retries = parse_int_env("AMAP_MAX_RETRIES", default=2)

        if not api_key:
            raise AmapConfigurationError("缺少环境变量 AMAP_API_KEY。")
        if not base_url:
            raise AmapConfigurationError("环境变量 AMAP_BASE_URL 不能为空。")
        if timeout_seconds <= 0:
            raise AmapConfigurationError("环境变量 AMAP_TIMEOUT_SECONDS 必须大于 0。")
        if max_retries < 0:
            raise AmapConfigurationError("环境变量 AMAP_MAX_RETRIES 不能小于 0。")

        return cls(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
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

        body = self._send_with_retries(http_request)

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

    def _send_with_retries(self, http_request: request.Request) -> str:
        last_error: BaseException | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                with self._urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                    return response.read().decode("utf-8")
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise AmapToolError(f"高德 HTTP 请求失败：{exc.code} {detail}") from exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    reason = getattr(exc, "reason", exc)
                    raise AmapToolError(f"高德网络请求失败：{reason}") from exc
                time.sleep(min(2**attempt, 4))

        raise AmapToolError(f"高德网络请求失败：{last_error}") from last_error

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



def build_map_preview_lines(
    destination: str | None,
    origin: str | None = None,
    themes: list[str] | None = None,
    long_distance_transport_preference: str | None = None,
    local_transport_preference: str | None = None,
) -> list[str]:
    if not destination:
        return ["地图预览：当前还没有明确目的地，跳过地图查询。"]

    try:
        amap_client = AmapClient(AmapConfig.from_env())
    except AmapConfigurationError:
        return ["地图预览：未检测到 AMAP_API_KEY，跳过地图查询。"]

    try:
        destination_geocode = amap_client.geocode(destination)
    except AmapToolError as exc:
        return [f"地图预览失败：{exc}"]

    lines = [
        "地图预览：",
        f"- 目的地解析：{destination_geocode.formatted_address}",
        f"- 坐标：{destination_geocode.location.longitude},{destination_geocode.location.latitude}",
    ]
    if destination_geocode.city:
        lines.append(f"- 城市：{destination_geocode.city}")
    if destination_geocode.district:
        lines.append(f"- 区县：{destination_geocode.district}")

    if origin:
        lines.extend(
            build_route_preview_lines(
                amap_client,
                origin,
                destination_geocode,
                long_distance_transport_preference=long_distance_transport_preference,
                local_transport_preference=local_transport_preference,
            )
        )

    if themes:
        lines.extend(
            build_theme_poi_preview_lines(
                amap_client,
                themes,
                city=destination_geocode.city or destination,
                destination_scope=destination,
            )
        )

    return lines


def build_map_preview_lines_for_request(request: TravelRequest) -> list[str]:
    """根据完整旅行请求生成地图事实预览。

    这是 Agent 层优先使用的入口。它把 TravelRequest 中的交通偏好传给地图工具，
    避免用户已经选择飞机/高铁时，地图预览仍误打跨城驾车路线。
    """

    return build_map_preview_lines(
        destination=request.destination,
        origin=request.origin,
        themes=request.themes,
        long_distance_transport_preference=request.long_distance_transport_preference,
        local_transport_preference=request.local_transport_preference,
    )


def build_route_preview_lines(
    amap_client: AmapClient,
    origin: str,
    destination_geocode: GeocodeResult,
    long_distance_transport_preference: str | None = None,
    local_transport_preference: str | None = None,
) -> list[str]:
    try:
        origin_geocode = amap_client.geocode(origin)
    except AmapToolError as exc:
        return [f"- 出发地解析失败：{exc}"]

    lines = [f"- 出发地解析：{origin_geocode.formatted_address}"]
    origin_region = origin_geocode.city or origin_geocode.province
    destination_region = destination_geocode.city or destination_geocode.province

    if should_skip_cross_region_driving_route(
        origin_region=origin_region,
        destination_region=destination_region,
        long_distance_transport_preference=long_distance_transport_preference,
    ):
        preference = long_distance_transport_preference or "非自驾大交通"
        lines.append(
            f"- 大交通偏好：{preference}；地图工具暂不估算跨城驾车路线。"
        )
        if local_transport_preference:
            lines.append(f"- 当地交通偏好：{local_transport_preference}")
        return lines

    try:
        if origin_region and destination_region and origin_region == destination_region:
            route = amap_client.walking_route(
                origin_geocode.location,
                destination_geocode.location,
            )
            route_mode_label = "步行"
        else:
            route = amap_client.driving_route(
                origin_geocode.location,
                destination_geocode.location,
            )
            route_mode_label = "驾车"
    except AmapToolError as exc:
        lines.append(f"- 路线预览失败：{exc}")
        return lines

    lines.append(
        f"- 路线预览（{route_mode_label}）：约 {format_distance(route.distance_meters)} / {format_duration(route.duration_seconds)}"
    )
    if route.summary:
        lines.append(f"  - 摘要：{route.summary}")
    return lines


def should_skip_cross_region_driving_route(
    origin_region: str | None,
    destination_region: str | None,
    long_distance_transport_preference: str | None,
) -> bool:
    """判断是否应该跳过跨区域驾车路线。

    高德驾车路线适合自驾场景；如果用户明确说大交通是飞机、高铁或火车，
    跨城驾车距离会误导后续规划，因此只保留地点解析和交通偏好说明。
    """

    if not origin_region or not destination_region:
        return False
    if origin_region == destination_region:
        return False

    preference = normalize_transport_preference(long_distance_transport_preference)
    if preference is None:
        return False
    return preference not in {"自驾", "驾车"}


def normalize_transport_preference(value: str | None) -> str | None:
    """归一化交通偏好关键词。"""

    if value is None:
        return None

    text = value.strip().lower()
    if not text:
        return None

    if any(keyword in text for keyword in ["飞机", "航班", "机票", "flight"]):
        return "飞机"
    if any(keyword in text for keyword in ["高铁", "动车", "火车", "铁路", "train"]):
        return "高铁"
    if any(keyword in text for keyword in ["自驾", "开车", "租车", "驾车", "drive"]):
        return "自驾"
    if any(keyword in text for keyword in ["都可以", "无所谓", "不限", "flexible"]):
        return "都可以"
    return value.strip()


def build_theme_poi_preview_lines(
    amap_client: AmapClient,
    themes: list[str],
    city: str,
    destination_scope: str | None = None,
) -> list[str]:
    poi_queries = build_poi_preview_queries_with_llm(
        city=city,
        themes=themes,
        destination_scope=destination_scope,
    )
    if not poi_queries:
        return []

    try:
        candidates = collect_theme_pois(amap_client, city, poi_queries)
    except AmapToolError as exc:
        return [f"- POI 预览失败：{exc}"]

    selected = select_distinct_preview_pois(candidates, limit=3)
    if not selected:
        return ["- 当前主题较抽象，暂未找到合适的 POI 预览结果。"]

    lines = ["- 主题 POI 预览："]
    for theme_label, keyword, poi in selected:
        parts = [poi.name]
        if poi.address:
            parts.append(poi.address)
        if poi.poi_type:
            parts.append(f"类型：{poi.poi_type}")
        lines.append(f"  - {'；'.join(parts)}（{theme_label}，按“{keyword}”检索）")
    return lines


def collect_theme_pois(
    amap_client: AmapClient,
    city: str,
    poi_queries: list[tuple[str, str]],
) -> list[tuple[str, str, AmapPOI]]:
    candidates: list[tuple[str, str, AmapPOI]] = []
    last_error: AmapToolError | None = None

    for theme_label, keyword in poi_queries[:6]:
        try:
            pois = amap_client.search_poi(keyword=keyword, city=city, offset=8)
        except AmapToolError as exc:
            last_error = exc
            continue

        for poi in pois:
            if is_transport_or_subpoi(poi):
                continue
            candidates.append((theme_label, keyword, poi))

    if not candidates and last_error is not None:
        raise last_error
    return candidates


def select_distinct_preview_pois(
    candidates: list[tuple[str, str, AmapPOI]],
    limit: int = 3,
) -> list[tuple[str, str, AmapPOI]]:
    selected_by_name: dict[str, tuple[int, tuple[str, str, AmapPOI]]] = {}

    for candidate in candidates:
        _, _, poi = candidate
        canonical_name = canonicalize_poi_name(poi.name)
        if not canonical_name:
            continue

        score = poi_place_score(poi)
        current = selected_by_name.get(canonical_name)
        if current is None or score > current[0]:
            selected_by_name[canonical_name] = (score, candidate)

    ranked = sorted(
        selected_by_name.values(),
        key=lambda item: item[0],
        reverse=True,
    )
    return [candidate for _, candidate in ranked[:limit]]


def canonicalize_poi_name(name: str) -> str:
    text = name.strip()
    text = re.sub(r"[（(].*?[）)]", "", text)
    for suffix in ["景区", "风景区", "地铁站", "公交站", "步行街", "停车场", "游客中心"]:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.strip()


def is_transport_or_subpoi(poi: AmapPOI) -> bool:
    text = " ".join(
        value
        for value in [poi.name, poi.poi_type, poi.address]
        if value
    )
    blocked_keywords = [
        "地铁站",
        "公交站",
        "停车场",
        "停车区",
        "出入口",
        "入口",
        "出口",
        "大门",
        "道路名",
        "道路",
        "交通设施服务",
    ]
    return any(keyword in text for keyword in blocked_keywords)


def poi_place_score(poi: AmapPOI) -> int:
    text = " ".join(
        value
        for value in [poi.name, poi.poi_type, poi.address]
        if value
    )
    score = 0
    preferred_keywords = [
        "风景名胜",
        "旅游景点",
        "名胜古迹",
        "博物馆",
        "特色商业街",
        "步行街",
        "公园",
        "景区",
    ]
    for keyword in preferred_keywords:
        if keyword in text:
            score += 3
    if poi.address:
        score += 1
    if poi.location:
        score += 1
    return score


def build_poi_preview_queries_with_llm(
    city: str,
    themes: list[str],
    destination_scope: str | None = None,
) -> list[tuple[str, str]]:
    try:
        llm_client = DeepSeekChatClient(LLMConfig.from_env())
    except LLMConfigurationError:
        return build_poi_preview_queries(themes)

    try:
        response = llm_client.chat(
            build_theme_poi_query_messages(
                destination=city,
                themes=themes,
                destination_scope=destination_scope,
            ),
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = parse_json_object(response.content)
    except LLMProviderError:
        return build_poi_preview_queries(themes)

    queries_data = data.get("queries")
    if not isinstance(queries_data, list):
        return build_poi_preview_queries(themes)

    queries: list[tuple[str, str]] = []
    seen_queries: set[str] = set()
    for item in queries_data:
        if not isinstance(item, dict):
            continue
        theme = as_optional_string(item.get("theme"))
        query = as_optional_string(item.get("query"))
        if not theme or not query or query in seen_queries:
            continue
        seen_queries.add(query)
        queries.append((theme, query))

    return queries or build_poi_preview_queries(themes)


def build_poi_preview_queries(themes: list[str]) -> list[tuple[str, str]]:
    theme_query_map = {
        "城市漫游": ["历史街区", "步行街", "胡同"],
        "city walk": ["历史街区", "步行街", "胡同"],
        "美食": ["美食街", "小吃街", "餐饮"],
        "小吃": ["小吃街", "小吃"],
        "夜市": ["夜市", "小吃街"],
        "海岛": ["海滩", "海岛景区"],
        "购物": ["商场", "步行街"],
        "逛街": ["步行街", "商圈"],
        "博物馆": ["博物馆"],
        "古迹": ["古迹", "名胜古迹"],
        "历史": ["历史街区", "古迹"],
    }
    generic_themes = {"轻松", "休闲", "放松", "旅行", "游玩", "度假"}

    queries: list[tuple[str, str]] = []
    seen_queries: set[str] = set()

    for theme in themes:
        normalized_theme = theme.strip()
        if not normalized_theme:
            continue

        candidate_queries = theme_query_map.get(normalized_theme)
        if candidate_queries is None:
            candidate_queries = theme_query_map.get(normalized_theme.lower())

        if candidate_queries is None:
            if normalized_theme in generic_themes:
                continue
            candidate_queries = [normalized_theme]

        for query in candidate_queries:
            if query in seen_queries:
                continue
            seen_queries.add(query)
            queries.append((normalized_theme, query))

    return queries


def format_distance(distance_meters: int | None) -> str:
    if distance_meters is None:
        return "未知距离"
    if distance_meters >= 1000:
        return f"{distance_meters / 1000:.1f}公里"
    return f"{distance_meters}米"


def format_duration(duration_seconds: int | None) -> str:
    if duration_seconds is None:
        return "未知时长"
    total_minutes = max(1, round(duration_seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes}分钟"
    if minutes == 0:
        return f"{hours}小时"
    return f"{hours}小时{minutes}分钟"


def parse_float_env(name: str, default: float) -> float:
    """读取 float 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise AmapConfigurationError(f"环境变量 {name} 必须是数字。") from exc


def parse_int_env(name: str, default: int) -> int:
    """读取 int 类型环境变量。"""

    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise AmapConfigurationError(f"环境变量 {name} 必须是整数。") from exc


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
