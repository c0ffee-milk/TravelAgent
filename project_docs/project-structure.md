# 项目目录规范

TravelAgent 仓库分为项目说明、教学文本和 Agent 工程三部分。这个结构用于避免教学材料和最终可运行 Agent 项目混在一起。

## 目标结构

```text
TravelAgent/
  README.md
  project_docs/
    architecture.md
    tech-stack.md
    business-scenarios.md
    data-and-apis.md
    course-roadmap.md
    project-structure.md
    00-reference-projects.md
  course/
    README.md
    lesson_00_project_bootstrap.md
    lesson_01_requirement_clarification.md
  agent/
    README.md
    pyproject.toml
    configs/
      .env.example
    src/
      travel_agent/
        README.md
    data/
      README.md
      mock/
      knowledge_base/
      eval/
    evals/
      README.md
    scripts/
      README.md
    app/
      README.md
```

## 目录职责

| 目录 | 职责 |
| --- | --- |
| `project_docs/` | 架构、技术栈、业务、数据/API、课程路线和参考调研 |
| `course/` | 教学文本和 lesson 课案 |
| `agent/` | 未来完整可独立运行的 Agent 工程 |
| `agent/configs/` | 环境变量样例和后续配置模板 |
| `agent/src/travel_agent/` | 后续存放可复用 Agent 代码 |
| `agent/data/mock/` | 后续存放 mock API 响应和教学样例 |
| `agent/data/knowledge_base/` | 后续存放目的地知识库材料 |
| `agent/data/eval/` | 后续存放评估任务集 |
| `agent/evals/` | 后续存放评估规则和 runner |
| `agent/scripts/` | 后续存放辅助脚本 |
| `agent/app/` | 后续预留 FastAPI/Web 服务 |

## Lesson 命名规范

具体 lesson 文件在用户要求生成时创建：

```text
course/lesson_00_topic_name.md
```

命名要求：

- 使用两位数字编号。
- 使用英文小写和下划线。
- 文件名表达本课主题。
- 不再为每节课创建文件夹。
- 每节课都要说明对应的 `agent/` 增量模块。
