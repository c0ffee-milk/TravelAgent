# travel_agent 包占位说明

本目录预留给后续可复用 Agent 代码，属于 `agent/` 独立工程的一部分。

课程文档位于 `../../../course/`。每一节课都会围绕本目录逐步增加或修改模块。

当前已放入注释型骨架：

- `schemas.py`：第 00 课的业务对象建模锚点。
- `clarification.py`：第 01 课的自然澄清状态与规则 fallback 锚点。
- `llm_provider.py`：第 02 课的 DeepSeek/OpenAI-compatible 调用封装与自然澄清 prompt。
- `map_tools.py`：第 03 课的高德地图工具层锚点。
- `weather_tools.py`：第 04 课的和风天气工具层锚点。

这些文件会随着课程逐步从注释和基础封装演进为完整 Agent 实现。
