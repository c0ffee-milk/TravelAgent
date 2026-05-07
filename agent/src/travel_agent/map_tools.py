"""TravelAgent 的高德地图工具设计说明。

本文件对应第 03 课：地图工具。

这一课的目标不是让 Agent 直接“会规划”，而是先给 Agent 增加一组可以被调用的地图工具。
后续 ReAct / Plan-and-Execute 课程会让模型根据任务动态选择这些工具。
"""

# 待办（第 03 课）：定义高德地图默认服务地址。
# - DEFAULT_AMAP_BASE_URL：默认值建议为 "https://restapi.amap.com"
# - 当前只需要从环境变量读取 AMAP_API_KEY，不要把真实 key 写进代码。

# 待办（第 03 课）：定义地图工具配置对象。
# 建议命名为 AmapConfig，并包含：
# - api_key：高德 Web 服务 API key
# - base_url：高德 REST API 根地址
# - timeout_seconds：HTTP 请求超时时间
# 需要提供 from_env()，从环境变量 AMAP_API_KEY 读取 key。

# 待办（第 03 课）：定义地图工具异常。
# 建议至少区分：
# - AmapConfigurationError：缺少 AMAP_API_KEY 等配置问题
# - AmapToolError：HTTP 失败、高德返回 status=0、响应结构异常等运行问题

# 待办（第 03 课）：定义通用坐标结构。
# 高德 Web 服务使用 "经度,纬度" 格式，例如 "116.397499,39.908722"。
# 建议封装为 Coordinate：
# - longitude：经度
# - latitude：纬度
# - to_amap_location()：返回 "longitude,latitude"

# 待办（第 03 课）：定义地理编码结果结构。
# 建议命名为 GeocodeResult，并包含：
# - formatted_address：匹配到的地址
# - province：省份
# - city：城市
# - district：区县
# - adcode：行政区划编码
# - location：Coordinate
# - level：匹配级别
# - raw：原始响应片段，便于后续 trace 和排查

# 待办（第 03 课）：定义 POI 结果结构。
# 建议命名为 AmapPOI，并包含：
# - poi_id：高德 POI ID
# - name：名称
# - poi_type：POI 类型
# - address：地址
# - city：城市
# - location：Coordinate
# - distance：距离，可选
# - raw：原始响应片段
# 后续可以把 AmapPOI 转换成 schemas.py 中的 POI。

# 待办（第 03 课）：定义路线结果结构。
# 建议命名为 RouteResult，并包含：
# - origin：起点 Coordinate
# - destination：终点 Coordinate
# - mode：walking / driving / transit
# - distance_meters：距离，单位米
# - duration_seconds：耗时，单位秒
# - summary：路线摘要
# - steps：路线步骤文本
# - raw：原始响应片段

# 待办（第 03 课）：定义 AmapClient。
# 它应该负责：
# - 接收 AmapConfig
# - 统一拼接 GET 请求参数
# - 自动带上 key 和 output=json
# - 检查高德响应中的 status
# - 把原始 JSON 转换成项目内部结构
# 这一层不要写“旅游推荐理由”，只负责地图事实查询。

# 待办（第 03 课）：实现 geocode(address, city=None)。
# 对应高德地理编码接口：
# - GET /v3/geocode/geo
# - 关键参数：address、city、key、output=json
# 用途：
# - 把“东京塔”“上海外滩”“北京南站”这类地点转成坐标。
# - 为后续 POI 搜索和路线规划提供稳定坐标。

# 待办（第 03 课）：实现 search_poi(keyword, city=None, types=None, page=1, offset=10)。
# 对应高德关键字搜索接口：
# - GET /v3/place/text
# - 关键参数：keywords、city、types、page、offset、key、output=json
# 用途：
# - 查询景点、餐厅、商圈、车站、酒店区域等候选地点。
# - 注意 offset 不要过大，避免无意义消耗配额。

# 待办（第 03 课）：实现 walking_route(origin, destination)。
# 对应高德步行路径规划接口：
# - GET /v3/direction/walking
# - 关键参数：origin、destination、key、output=json
# 用途：
# - 判断两个 POI 之间是否适合步行。
# - 如果步行耗时过长，后续规划层应改用地铁、打车或调整顺序。

# 待办（第 03 课）：实现 driving_route(origin, destination)。
# 对应高德驾车路径规划接口：
# - GET /v3/direction/driving
# - 关键参数：origin、destination、strategy、key、output=json
# 用途：
# - 估算打车或自驾移动成本。
# - 注意路线结果会随道路、交通和算法变化，不能当成永久事实。

# 待办（第 03 课）：设计工具描述。
# 后续让 LLM 做工具调用时，需要把工具暴露成清晰的 schema：
# - tool name：geocode / search_poi / walking_route / driving_route
# - description：什么时候使用
# - parameters：字段名、类型、是否必填
# - return shape：返回哪些结构化字段

# 待办（第 03 课）：设计 mock fallback。
# 如果没有 AMAP_API_KEY，或者真实 API 请求失败，后续可以从 agent/data/mock/ 读取固定样例。
# mock 只用于教学和测试，不能伪装成实时地图结果。
