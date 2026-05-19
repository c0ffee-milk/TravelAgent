# Lesson 04：和风天气工具

本节把 TravelAgent 的外部工具能力从“地图事实”扩展到“天气风险”。旅行规划不是只把景点串起来，还要判断天气是否会影响户外活动、交通移动、穿衣准备和备选方案。

本节先新增 `weather_tools.py` 注释骨架，规划如何接入和风天气 GeoAPI 和逐日天气预报。它未来只负责查询天气事实和生成风险提示，不生成完整行程。

## 本节目标

完成本节后，你应该能够：

- 理解天气工具在旅行规划中的作用。
- 区分“短期真实预报”和“远期季节性参考”。
- 使用和风 GeoAPI 把目的地转换成 Location ID。
- 使用逐日天气预报获取未来几天的天气。
- 把天气事实转换成 Agent 可用的风险提示。
- 理解为什么天气工具不能替代最终行程规划器。

## 基础知识

### 1. 天气为什么是独立 Tool

LLM 可以知道某地大致气候，但不能可靠知道实时天气。旅游规划里这些问题应该来自天气 API：

- 未来几天是否下雨。
- 是否有高温、低温、大风、强紫外线。
- 户外景点是否需要备选方案。
- 是否需要提醒用户带雨具、防晒或保暖衣物。
- 临时改行程时，是否应该把户外活动换成室内活动。

天气工具的职责是提供事实和风险，不负责直接安排“第几天去哪”。

### 2. 和风天气的两步查询

和风天气的天气预报接口通常不直接用城市中文名，而是使用 Location ID。

因此本节采用两步：

```text
目的地名称 -> GeoAPI 城市查询 -> Location ID -> 逐日天气预报
```

对应接口：

```text
GET /geo/v2/city/lookup
GET /v7/weather/{days}
```

官方文档说明，GeoAPI 城市查询可以返回城市 ID、名称、经纬度、时区和行政区信息；逐日天气预报支持 3d、7d、10d、15d、30d 等天数。

### 3. 短期预报和远期旅行

如果用户说“明年 9 月去西藏”，当前真实天气预报无法覆盖这个时间。此时 Agent 不能把今天的天气误当作明年的天气。

本节实现时应采用保守策略：

- 近期或未明确年份：可以查询短期预报。
- 明确是明年、后年、春节、五一、国庆等远期时间：跳过真实预报，只提示临近出行时复查天气。

后续如果要做季节性气候建议，应单独接目的地知识库或历史气候数据，而不是复用短期预报。

## 真实 API 配置

在 `agent/.env` 中配置：

```dotenv
QWEATHER_API_KEY=你的和风天气 token 或 key
QWEATHER_BASE_URL=https://devapi.qweather.com
QWEATHER_AUTH_MODE=auto
QWEATHER_TIMEOUT_SECONDS=30
QWEATHER_MAX_RETRIES=2
```

说明：

- 和风天气新版官方示例支持 JWT `Authorization: Bearer <token>`，普通 API KEY 推荐使用 `X-QW-Api-Key` 请求头，也可以使用 query `key=`。
- 本项目默认 `QWEATHER_AUTH_MODE=auto`：JWT 三段式 token 自动走 `bearer`，普通 API KEY 自动走 `header_key`。
- 如果你的账号仍使用旧式 query key，可以改成：

```dotenv
QWEATHER_AUTH_MODE=query_key
```

测试前加载本地环境：

```bash
cd agent
set -a
source .env
set +a
```

不要打印完整 API key。只检查长度即可：

```bash
python - <<'PY'
import os
print("QWEATHER_API_KEY length:", len(os.getenv("QWEATHER_API_KEY", "")))
PY
```

## 本节要修改的 Agent 模块

本节新增骨架：

- `agent/src/travel_agent/weather_tools.py`：和风天气工具层。

本节更新：

- `agent/scripts/demo_clarification_chat.py`：在信息足够时打印天气预览。
- `agent/configs/.env.example`：增加和风天气配置项。
- `agent/src/travel_agent/README.md`：加入 Lesson 04 模块说明。
- `course/README.md`：加入 Lesson 04 指导书索引。

## 推荐搭建步骤

### Step 1：定义工具边界

先在 `weather_tools.py` 中定义：

- `QWeatherConfig`：读取 key、API Host、认证模式、超时和重试。
- `QWeatherConfigurationError`：配置错误。
- `QWeatherToolError`：调用失败或响应解析失败。
- `WeatherLocation`：GeoAPI 地点结果。
- `DailyWeather`：单日天气预报。
- `WeatherForecast`：逐日天气预报结果。
- `WeatherRisk`：天气风险提示。
- `QWeatherClient`：和风天气客户端。

这些对象的目标是让天气工具输出结构化事实，而不是散落的字符串。

### Step 2：实现城市查询

城市查询接口：

```text
GET /geo/v2/city/lookup
```

核心参数：

```text
location=目的地名称
number=结果数量
range=cn
lang=zh
```

返回结果中最重要的是：

- `location.id`
- `location.name`
- `location.adm1`
- `location.adm2`
- `location.country`
- `location.lat`
- `location.lon`
- `location.tz`

后续天气查询使用 `location.id`。

### Step 3：实现逐日天气预报

天气预报接口：

```text
GET /v7/weather/{days}
```

本节支持：

- `3d`
- `7d`
- `10d`
- `15d`
- `30d`

核心参数：

```text
location=Location ID
lang=zh
unit=m
```

本节至少解析：

- 日期。
- 白天/夜间天气。
- 最高/最低温度。
- 风向、风力、风速。
- 湿度。
- 降水量。
- 紫外线指数。
- 能见度。

### Step 4：生成天气风险

天气风险不是最终行程，只是后续规划器的输入。

本节先做规则型判断：

- 出现雨、雪、雷、冰雹或较大降水量：提示降水影响。
- 最高温度大于等于 35℃：提示高温风险。
- 最低温度小于等于 0℃：提示低温风险。
- 风力大于等于 6 级：提示大风风险。
- 紫外线指数大于等于 8：提示强紫外线。

后续规划器可以根据这些风险调整活动类型，例如把户外景点换成博物馆、商圈、演出或酒店休息。

### Step 5：预留 Demo 接入点

等你完成 `weather_tools.py` 的真实代码后，可以让 demo 在需求澄清 ready 时依次打印：

```text
地图预览：
...
天气预览：
...
```

如果没有配置 `QWEATHER_API_KEY`，天气工具应该优雅跳过：

```text
天气预览：未检测到 QWEATHER_API_KEY，跳过天气查询。
```

如果出行时间是远期：

```text
天气预览：当前出行时间不在短期天气预报窗口内。
- 天气工具将在临近出行时查询实时预报；当前只记录目的地天气风险需要后续复查。
```

## 关键设计取舍

- 天气工具不直接安排路线，只提供天气事实和风险。
- 远期旅行不调用短期预报，避免误导。
- 天气风险先用规则判断，不急着让 LLM 解释。
- 和风认证模式保留 `bearer` 和 `query_key` 两种配置，适配不同账号形态。
- 等你完成实现后，demo 只应调用 `build_weather_preview_lines_for_request()`，业务判断放在 `weather_tools.py`。

## 运行检查

先做无网络语法检查：

```bash
cd agent
python -m py_compile src/travel_agent/weather_tools.py scripts/demo_clarification_chat.py
```

等你把 `QWeatherClient` 和 `QWeatherConfig` 补齐后，再做真实 API 测试：

```bash
cd agent
set -a
source .env
set +a
python - <<'PY'
from travel_agent.weather_tools import QWeatherClient, QWeatherConfig

client = QWeatherClient(QWeatherConfig.from_env())
location = client.lookup_city("北京")[0]
forecast = client.daily_forecast(location.location_id, days="3d")

print(location.name, location.location_id)
for item in forecast.daily:
    print(item.forecast_date, item.text_day, item.temp_min, item.temp_max)
PY
```

如果认证失败，优先检查：

- `QWEATHER_API_KEY` 是否是当前 API Host 对应的 token。
- `QWEATHER_BASE_URL` 是否是控制台提供的 API Host。
- `QWEATHER_AUTH_MODE` 是否应从 `auto` 改为 `bearer`、`header_key` 或 `query_key`。

## 自检标准

完成本节后，你应该能回答：

- 为什么天气工具需要先查 Location ID？
- 为什么远期旅行不能直接使用短期天气预报？
- `WeatherRisk` 和最终行程调整之间是什么关系？
- 天气 API 失败时 demo 为什么不能崩溃？
- 哪些天气条件会影响户外行程？
- 这个工具后续如何服务 ReAct Agent 或规划型 Agent？

## 参考

- 和风 GeoAPI 城市查询：https://dev.qweather.com/en/docs/api/geoapi/city-lookup/
- 和风逐日天气预报：https://dev.qweather.com/docs/api/weather/weather-daily-forecast/
