# Course

本目录存放 TravelAgent 的教学指导书。每一节课程直接用一个 Markdown 文件表示，不再为每节课单独建文件夹。

当前已创建：

- `lesson_00_project_bootstrap.md`：项目启动与业务建模。
- `lesson_01_requirement_clarification.md`：LLM 驱动的自然需求澄清。
- `lesson_02_llm_provider.md`：LLM Provider 与自然澄清生成。
- `lesson_03_amap_tools.md`：高德地图工具。
- `lesson_04_weather_tools.md`：和风天气工具。

## 课程写法

每节课都面向学习者本人书写，相当于一份搭建指导书。每个 lesson 应包含：

- 本节目标。
- 需要掌握的基础知识。
- 本节要在 `agent/` 中新增或修改的模块。
- 建议的实现步骤。
- 关键设计取舍。
- 自检标准。

课程文本不单独保存完整代码。完整 Agent 工程位于 `../agent/`，每一节课都应是对 `agent/` 项目的增量搭建或修改。

## Agent 注释骨架

当某节课引入新的工程模块时，应在 `agent/` 对应文件中留下清晰注释，说明学习者需要完成什么。例如：

- Lesson 00：在 `agent/src/travel_agent/schemas.py` 中标注业务对象。
- Lesson 01：在 `agent/src/travel_agent/clarification.py` 中标注自然澄清状态。
- Lesson 02：在 `agent/src/travel_agent/llm_provider.py` 中封装 DeepSeek/OpenAI-compatible 调用和自然澄清 prompt。
- Lesson 03：在 `agent/src/travel_agent/map_tools.py` 中标注高德地图工具边界。
- Lesson 04：在 `agent/src/travel_agent/weather_tools.py` 中标注和风天气工具边界。

这些注释是搭建指引，不等于完整实现。

## 课程约束

- 所有 lesson 必须围绕同一个旅游规划业务逐步升级。
- 教学文档放在 `course/`。
- 完整 Agent 实现放在 `agent/`。
- 不再创建 `course/lesson_xx/` 文件夹。
