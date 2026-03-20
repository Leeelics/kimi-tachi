# Documentation Index

## 核心文档

| 文档 | 内容 | 适合人群 |
|------|------|----------|
| [README.md](../README.md) | 项目概览、安装、基础使用 | 所有人 |
| [QUICKSTART.md](./QUICKSTART.md) | 快速上手指南 | 新用户 |
| [VISION.md](./VISION.md) | 设计理念、角色设定 | 想深入理解的人 |
| [AGENTS.md](./AGENTS.md) | 开发指南、贡献规范、架构说明 | 贡献者、开发者 |
| [STATUS.md](./STATUS.md) | 当前状态、路线图 | 贡献者、用户 |
| [ROADMAP.md](./ROADMAP.md) | 详细路线图（基于 kimi-cli 分析） | 贡献者、核心用户 |

## 角色文档

每个角色的详细设定：

| Agent | 角色 | 文档 | 描述 |
|-------|------|------|------|
| kamaji | 釜爺 | [agents/kamaji.yaml](agents/kamaji.yaml) | 总协调者 |
| shishigami | 山兽神 | [agents/shishigami.yaml](agents/shishigami.yaml) | 架构师 |
| nekobasu | 猫巴士 | [agents/nekobasu.yaml](agents/nekobasu.yaml) | 侦察兵 |
| calcifer | 火魔 | [agents/calcifer.yaml](agents/calcifer.yaml) | 工匠 |
| enma | 阎魔王 | [agents/enma.yaml](agents/enma.yaml) | 审查员 |
| tasogare | 黄昏 | [agents/tasogare.yaml](agents/tasogare.yaml) | 规划师 |
| phoenix | 火之鸟 | [agents/phoenix.yaml](agents/phoenix.yaml) | 记忆 |

## Skill 文档

| Skill | 路径 | 描述 |
|-------|------|------|
| todo-enforcer | [skills/todo-enforcer/SKILL.md](skills/todo-enforcer/SKILL.md) | Todo 列表强制执行 |
| category-router | [skills/category-router/SKILL.md](skills/category-router/SKILL.md) | 智能任务路由 |

## 代码文档

| 文件 | 描述 |
|------|------|
| [src/kimi_tachi/cli.py](src/kimi_tachi/cli.py) | Typer CLI 实现 |
| [src/kimi_tachi/orchestrator/](src/kimi_tachi/orchestrator/) | Workflow 编排引擎 |

## 外部链接

- [Kimi CLI Repository](https://github.com/your-org/kimi-cli)
- [Kimi CLI Documentation](https://kimi-cli.readthedocs.io)
