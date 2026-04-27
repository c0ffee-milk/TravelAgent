# 项目目录规范

当前仓库只建立空骨架，不实现具体 lesson。

## 目标结构

```text
TravelAgent/
  README.md
  configs/
    .env.example
  docs/
    architecture.md
    tech-stack.md
    business-scenarios.md
    data-and-apis.md
    course-roadmap.md
    project-structure.md
    00-reference-projects.md
  lessons/
    README.md
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
| `configs/` | 环境变量样例和后续配置模板 |
| `docs/` | 架构、技术栈、业务、数据、课程路线文档 |
| `lessons/` | 后续按需生成具体 lesson |
| `src/travel_agent/` | 后续存放可复用 Agent 代码 |
| `data/mock/` | 后续存放 mock API 响应和教学样例 |
| `data/knowledge_base/` | 后续存放目的地知识库材料 |
| `data/eval/` | 后续存放评估任务集 |
| `evals/` | 后续存放评估规则和 runner |
| `scripts/` | 后续存放辅助脚本 |
| `app/` | 后续预留 FastAPI/Web 服务 |

## Lesson 命名规范

具体 lesson 目录在用户要求生成时创建：

```text
lessons/lesson_00_topic_name/
  README.md
  lesson_plan.md
  code/
  exercises.md
  acceptance.md
```

命名要求：

- 使用两位数字编号。
- 使用英文小写和下划线。
- 目录名表达本课主题。
- 不提前创建未实现 lesson。

