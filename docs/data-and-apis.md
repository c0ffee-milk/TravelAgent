# 数据来源与 API 前置条件

TravelAgent 按真实 API 优先设计，但当前阶段不实现任何调用代码。

## 环境变量

配置样例见 [configs/.env.example](../configs/.env.example)。

| 变量 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | DeepSeek OpenAI-compatible base URL |
| `DEEPSEEK_MODEL` | 默认模型名 |
| `AMAP_API_KEY` | 高德地图 API key |
| `QWEATHER_API_KEY` | 和风天气 API key |

## DeepSeek

用途：

- 需求理解。
- 结构化输出。
- 行程生成。
- 规划与重规划。
- 评估解释和自然语言总结。

调用边界：

- 后续实现时统一封装为 LLM Provider。
- lesson 代码不直接读取密钥。
- 所有 prompt、输入、输出应可记录 trace。

默认配置：

```text
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 高德地图 API

用途：

- 地理编码。
- POI 搜索。
- 城市和区域查询。
- 路线规划。
- 距离和交通耗时估算。

调用边界：

- 不把高德返回结果直接当作最终推荐，需要由 Agent 做筛选和解释。
- 路线结果应保留来源和查询参数。
- API 失败时，后续 lesson 可降级到本地 mock 数据。

## 和风天气 API

用途：

- 实况天气。
- 逐日天气预报。
- 降雨、高温、低温、台风等风险提示。
- 临时改行程时提供室内/室外调整依据。

调用边界：

- 天气信息必须带查询地点和日期。
- 长期旅行规划只应把远期天气作为趋势参考。
- 重要风险需提示用户以官方预警为准。

## 酒店、航班、火车票

第一阶段不接真实交易 API，只规划 Tool Contract：

- 酒店：位置、价格区间、评分、适合人群、交通便利度。
- 航班：出发/到达城市、日期、价格区间、耗时、经停。
- 火车票：车次、耗时、价格区间、站点、余票状态。

后续如接真实服务，需要单独处理：

- API 资质和合规。
- 价格实时性。
- 库存变化。
- 支付和退改签边界。

## Mock 数据策略

虽然真实 API 优先，但每个真实工具都应有 mock fallback：

- 便于无 key 学习。
- 便于测试稳定。
- 便于演示 API 失败时的降级逻辑。

mock 数据只放固定示例，不伪装成实时真实结果。

