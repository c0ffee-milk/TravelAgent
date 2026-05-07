# Scripts

本目录存放教学阶段的辅助脚本。

当前已有：

- `demo_clarification_chat.py`：Lesson 00-02 可对话需求澄清 demo。

后续可能加入：

- 环境检查。
- lesson 运行入口。
- 数据准备。
- 评估执行。
- 报告生成。

## demo_clarification_chat.py

运行方式：

```bash
cd agent
python scripts/demo_clarification_chat.py
```

这个 demo 会自动尝试读取：

- `agent/.env`
- `agent/configs/.env`

如果没有本地 `.env`，也可以先手动加载环境变量：

```bash
cd agent
set -a
source .env
set +a
python scripts/demo_clarification_chat.py
```

当前 demo 只串联：

- `schemas.py`
- `clarification.py`
- `llm_provider.py`

它不会生成完整行程，也不会调用地图、天气、酒店或航班 API。
