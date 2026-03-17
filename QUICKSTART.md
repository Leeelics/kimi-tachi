# Quick Start

## 1. 安装

```bash
# 安装 kimi-tachi
pip install -e .

# 安装到 Kimi CLI
kimi-tachi install
```

## 2. 验证安装

```bash
kimi-tachi status
```

## 3. 基础使用

```bash
# 使用默认的 sisyphus 启动
kimi-tachi run

# 使用特定代理
kimi-tachi run --agent oracle

# Plan Mode
kimi-tachi run --agent prometheus --plan

# One-shot 模式
kimi-tachi do "Implement user authentication"
```

## 4. 查看可用代理

```bash
kimi-tachi list-agents
```

## 5. 在 Kimi CLI 中直接使用

```bash
# 安装后，可以直接在 Kimi CLI 中加载代理
kimi --agent ~/.kimi/agents/kimi-tachi/sisyphus.yaml

# 或使用其他代理
kimi --agent ~/.kimi/agents/kimi-tachi/oracle.yaml
```

## 6. 使用 Skills

在 Kimi 中通过斜杠命令使用 Skills：

```
/skill:todo-enforcer
/skill:category-router
```

## 架构

```
kimi-tachi/
├── agents/              # Agent YAML 配置
│   ├── sisyphus.yaml   # 总指挥官
│   ├── oracle.yaml     # 架构师
│   ├── hermes.yaml     # 侦察兵
│   ├── hephaestus.yaml # 工匠
│   ├── momus.yaml      # 审查员
│   ├── prometheus.yaml # 规划师
│   └── librarian.yaml  # 图书管理员
├── skills/             # Skill 定义
│   ├── todo-enforcer/
│   └── category-router/
└── src/kimi_tachi/     # CLI 代码
```

## 七人衆 (The Seven)

| 代理 | 角色 | 职责 |
|------|------|------|
| sisyphus | 総指揮 | 任务编排、代理调度 |
| oracle | 神託 | 架构决策、技术选型 |
| hermes | 探索 | 代码探索、快速定位 |
| hephaestus | 工匠 | 深度实现、代码编写 |
| momus | 監視 | 代码审查、质量保障 |
| prometheus | 予見 | 规划分析、调研 |
| librarian | 知識 | 文档管理、知识整理 |

## 多代理委派示例

在 sisyphus 中，可以直接使用 Task 工具委派给其他代理：

```python
# sisyphus 会自动使用 Task 工具
Task(
    description="Explore codebase structure",
    subagent_name="hermes",
    prompt="Find all API endpoint definitions in this project"
)
```

## 注意事项

- 需要 Kimi CLI >= 1.19.0（支持原生 Task 工具）
- Agents 安装在 `~/.kimi/agents/kimi-tachi/`
- Skills 安装在 `~/.kimi/skills/`
