# Lesson 03：高德地图工具

从这一节开始，TravelAgent 不再只处理用户文本，而是要接入外部世界的数据。地图工具是第一个 Tool Layer：它负责把“地点名称、景点、餐厅、路线距离、移动时间”变成可验证的结构化信息。

本节你要完成的是高德地图工具的模块设计和实现准备。它不负责生成完整旅行方案，也不负责判断“哪里更好玩”。它只回答地图事实问题：地点在哪里、附近有什么、两个地点之间怎么走、大概要多久。

## 本节目标

完成本节后，你应该能够：

- 理解 Agent 为什么需要 Tool Layer。
- 区分 LLM 生成内容和外部工具返回事实。
- 知道高德地图 Web 服务 API 的配置方式。
- 设计地理编码、POI 搜索、路线规划三类地图工具。
- 明确工具输入、输出、异常和降级策略。
- 为后续 ReAct Agent 的工具调用准备参数 schema。

## 基础知识

### 1. Tool Layer 是什么

LLM 擅长理解意图和组织语言，但不适合凭空回答实时或半实时事实。旅行规划里有很多信息应该来自工具：

- 地点是否存在。
- 景点或餐厅在哪个城市。
- 两个地点之间距离多远。
- 步行是否可接受。
- 打车或自驾大概需要多久。
- 某个城市内有哪些候选 POI。

Tool Layer 的职责是把这些事实查出来，并用稳定结构返回给 Agent Core。

### 2. 地图工具和 LLM Provider 的区别

Lesson 02 的 `llm_provider.py` 只负责调用模型：

```text
自然语言上下文 -> 模型文本或 JSON
```

Lesson 03 的地图工具负责调用高德：

```text
结构化参数 -> 地图事实数据
```

不要让地图工具直接写旅行推荐文案。推荐理由、取舍和行程安排应该留给后续规划层处理。

### 3. 高德坐标格式

高德 Web 服务使用：

```text
经度,纬度
```

例如：

```text
116.397499,39.908722
```

你后续写 `Coordinate` 时，要避免把纬度和经度顺序写反。路线规划、周边搜索都依赖这个格式。

## 真实 API 配置

本节使用高德地图 Web 服务 API。你需要在高德开放平台创建 Web 服务类型的 Key。

环境变量沿用：

```dotenv
AMAP_API_KEY=你的高德 Web 服务 API key
```

配置位置：

```text
agent/configs/.env.example
```

如果你在 `agent/` 目录下用 `.env` 保存本地配置，测试前需要加载：

```bash
cd agent
set -a
source .env
set +a
```

确认变量是否加载时，不要打印完整 key：

```bash
python - <<'PY'
import os
print("AMAP_API_KEY length:", len(os.getenv("AMAP_API_KEY", "")))
PY
```

## 本节要修改的 Agent 模块

本节新增：

- `agent/src/travel_agent/map_tools.py`：高德地图工具层骨架。

本节更新：

- `agent/src/travel_agent/README.md`：加入 Lesson 03 模块说明。
- `course/README.md`：加入 Lesson 03 指导书索引。

## 推荐搭建步骤

### Step 1：先定义工具边界

在 `agent/src/travel_agent/map_tools.py` 中先定义这些对象：

- `AmapConfig`：读取 `AMAP_API_KEY` 和默认服务地址。
- `AmapConfigurationError`：配置错误。
- `AmapToolError`：调用失败或响应解析失败。
- `Coordinate`：统一坐标格式。
- `GeocodeResult`：地理编码结果。
- `AmapPOI`：POI 搜索结果。
- `RouteResult`：路线结果。
- `AmapClient`：高德 Web 服务客户端。

这些对象的重点不是“写得复杂”，而是让后续 Agent 调用时有稳定输入输出。

### Step 2：实现地理编码工具

地理编码用于把地址或地点名称转换为坐标。

接口：

```text
GET https://restapi.amap.com/v3/geocode/geo
```

核心参数：

```text
key=AMAP_API_KEY
address=结构化地址或地点名称
city=可选城市
output=json
```

你可以先用 curl 测试：

```bash
curl "https://restapi.amap.com/v3/geocode/geo?address=天安门&city=北京&output=json&key=$AMAP_API_KEY"
```

你在代码里至少要解析：

- `status`
- `info`
- `geocodes[0].formatted_address`
- `geocodes[0].province`
- `geocodes[0].city`
- `geocodes[0].district`
- `geocodes[0].adcode`
- `geocodes[0].location`
- `geocodes[0].level`

如果 `status` 不是 `"1"`，不要继续假装成功，应该抛出 `AmapToolError`。

### Step 3：实现 POI 关键字搜索

POI 搜索用于找候选景点、餐厅、商圈、交通站点。

接口：

```text
GET https://restapi.amap.com/v3/place/text
```

核心参数：

```text
key=AMAP_API_KEY
keywords=查询关键词
city=可选城市
types=可选 POI 类型
page=页码
offset=每页数量
output=json
```

你可以先用 curl 测试：

```bash
curl "https://restapi.amap.com/v3/place/text?keywords=博物馆&city=北京&offset=5&page=1&output=json&key=$AMAP_API_KEY"
```

在旅游规划业务里，POI 搜索不要一次拉太多。推荐先用 `offset=5` 或 `offset=10`，让 Agent 后续根据主题、预算、节奏再筛选。

### Step 4：实现路线规划工具

路线规划用于判断行程是否可执行。

本节先关注两种模式：

- 步行：判断两个 POI 是否适合步行串联。
- 驾车：粗略估算打车或自驾移动时间。

步行接口：

```text
GET https://restapi.amap.com/v3/direction/walking
```

驾车接口：

```text
GET https://restapi.amap.com/v3/direction/driving
```

核心参数：

```text
key=AMAP_API_KEY
origin=起点经度,纬度
destination=终点经度,纬度
output=json
```

测试示例：

```bash
curl "https://restapi.amap.com/v3/direction/walking?origin=116.397499,39.908722&destination=116.403963,39.915119&output=json&key=$AMAP_API_KEY"
```

路线结果至少要转成：

- 距离，单位米。
- 耗时，单位秒。
- 路线摘要。
- 分步说明。
- 原始响应片段。

### Step 5：把工具设计成可被 LLM 调用

虽然本节还不实现完整 tool calling，但你应该从现在开始按工具 schema 思考。

示例：

```text
tool name: geocode
description: 把地点名称或结构化地址转换为高德坐标。
parameters:
  address: string, required
  city: string, optional
returns:
  formatted_address
  city
  district
  location
```

后续 ReAct Agent 会根据问题选择工具，例如：

```text
用户：我想住在外滩附近，晚上能散步看夜景。
Agent 判断：
1. geocode("外滩", city="上海")
2. search_poi("酒店", city="上海", around=外滩坐标)
3. walking_route(酒店坐标, 外滩坐标)
```

### Step 6：设计降级策略

真实 API 会失败，常见原因包括：

- 没有配置 `AMAP_API_KEY`。
- key 类型不是 Web 服务 API。
- 配额用完。
- 参数格式错误。
- 地点名称歧义太大。
- 网络异常。

本节先在文档和注释里把 fallback 留出来。后续可以在 `agent/data/mock/` 放固定样例，让没有 key 的情况下也能学习工具调用流程。

mock 数据必须明确标记为示例数据，不要伪装成实时结果。

## 关键设计取舍

- 地图工具只返回事实数据，不写旅游文案。
- 工具输入尽量结构化，不要把整段用户自然语言直接丢给高德。
- 地理编码失败时应该追问或换关键词，而不是让 LLM 猜坐标。
- POI 搜索结果必须保留原始来源，便于后续 trace。
- 路线耗时会随现实情况变化，规划时要给用户留缓冲。
- 本节只设计高德工具，不引入 LangGraph 或完整 ReAct 循环。

## 自检标准

完成本节后，你应该能回答：

- 为什么地图事实不能只靠 LLM 生成？
- 高德坐标为什么要统一成“经度,纬度”？
- `geocode`、`search_poi`、`walking_route`、`driving_route` 分别解决什么问题？
- API 返回 `status=0` 时应该怎么处理？
- POI 搜索结果为什么不能直接等同于最终推荐？
- 路线结果如何影响旅游规划里的节奏和可行性？
- 这些工具后续如何暴露给 ReAct Agent？

## 参考

- 高德地理/逆地理编码 API：[https://lbs.amap.com/api/webservice/guide/api/georegeo](https://lbs.amap.com/api/webservice/guide/api/georegeo)
- 高德搜索 POI API：[https://lbs.amap.com/api/webservice/guide/api-advanced/search](https://lbs.amap.com/api/webservice/guide/api-advanced/search)
- 高德路径规划 API：[https://lbs.amap.com/api/webservice/guide/api/direction](https://lbs.amap.com/api/webservice/guide/api/direction)

