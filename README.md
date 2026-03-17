# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI
> 
> *Kimi-tachi* means "you all" or "Kimi team" in Japanese - a squad of specialized Kimi agents working together.

## 🎯 核心理念

**kimi-tachi** 是 Kimi CLI 的多代理编排层，通过原生扩展机制（Agent YAML + Skill + Tools）实现工程化可靠性，无需修改 Kimi CLI 源码。

### 与 Kimi CLI 的关系

```
┌─────────────────────────────────────────┐
│           kimi-tachi                    │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Agents  │ │ Skills  │ │  Tools   │  │
│  │ (YAML)  │ │(.md)    │ │(Python)  │  │
│  └────┬────┘ └────┬────┘ └────┬─────┘  │
│       └─────────────┴───────────┘       │
│                   │                     │
│              Native API                 │
│                   │                     │
└───────────────────┼─────────────────────┘
                    │
┌───────────────────┼─────────────────────┐
│              Kimi CLI                   │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │  Soul   │ │  Wire   │ │ Context  │  │
│  │  Task   │ │Skill Sys│ │Compaction│  │
│  └─────────┘ └─────────┘ └──────────┘  │
└─────────────────────────────────────────┘
```

## 🏛️ Agent 体系（七人衆）

| Agent | 角色 | 职责 | 模型建议 |
|-------|------|------|----------|
| **sisyphus** | 总指挥官 | 任务拆解、代理调度、结果整合 | kimi-k2.5 |
| **oracle** | 架构师 | 技术决策、架构设计、难点攻关 | kimi-k2.5 |
| **hermes** | 侦察兵 | 代码探索、快速定位、信息收集 | kimi-k2.5 |
| **hephaestus** | 工匠 | 深度实现、代码编写、重构 | kimi-k2.5 |
| **prometheus** | 规划师 | Plan Mode 专用、调研分析 | kimi-k2.5 |
| **momus** | 审查员 | 代码审查、安全审计、最佳实践 | kimi-k2.5 |
| **librarian** | 图书管理员 | 文档管理、知识整理、搜索 | kimi-k2.5 |

## 🛠️ 技术架构

### 1. 原生优先策略

| 功能 | 原设计方案 | 优化方案 | 理由 |
|------|-----------|----------|------|
| 子代理委派 | MCP + subprocess | **原生 Task 工具** | 无需额外进程，自动上下文隔离 |
| 文件编辑 | MCP hashline-edit | **原生 StrReplaceFile** | Kimi CLI 原生已足够强大 |
| 记忆系统 | 独立 MCP | **扩展 Context 类** | 直接访问内部状态 |
| 配置管理 | 独立配置文件 | **整合 config.toml** | 用户无需维护多份配置 |
| Wrapper | subprocess | **Typer CLI + import** | 直接调用 KimiCLI 类 |

### 2. 简化架构

```
kimi-tachi/
├── agents/                 # Agent YAML 定义
│   ├── sisyphus.yaml      # 总指挥官
│   ├── oracle.yaml        # 架构师
│   ├── hermes.yaml        # 侦察兵
│   ├── hephaestus.yaml    # 工匠
│   ├── prometheus.yaml    # 规划师
│   ├── momus.yaml         # 审查员
│   └── librarian.yaml     # 图书管理员
│
├── skills/                # Skill 定义（Markdown）
│   ├── todo-enforcer/
│   │   └── SKILL.md       # Todo 强制执行
│   ├── category-router/
│   │   └── SKILL.md       # 智能路由
│   └── prometheus/
│       └── SKILL.md       # Plan Mode 引导
│
├── tools/                 # 原生 Tools（可选增强）
│   ├── __init__.py
│   └── checkpoint.py      # 扩展 D-Mail 系统
│
├── src/
│   └── kimi_tachi/
│       ├── __init__.py
│       ├── cli.py         # Typer CLI
│       ├── config.py      # 配置整合
│       └── memory.py      # 增强记忆（Phase 2）
│
└── pyproject.toml
```

## 🚀 使用方式

### 安装

```bash
pip install kimi-tachi

# 安装到 Kimi CLI
kimi-tachi install
# 会自动：
# 1. 复制 agents/ 到 ~/.kimi/agents/kimi-tachi/
# 2. 复制 skills/ 到 ~/.kimi/skills/
# 3. 更新 ~/.kimi/config.toml
```

### 基础使用

```bash
# 使用总指挥官启动
kimi-tachi run

# 使用特定代理
kimi-tachi run --agent oracle
kimi-tachi run --agent hephaestus --yolo

# Plan Mode 启动
kimi-tachi run --agent prometheus --plan

# One-shot 模式
kimi-tachi do "实现用户认证系统"
```

### 在 Kimi CLI 中直接使用

```bash
# 安装后，可以直接在 Kimi CLI 中加载
kimi --agent ~/.kimi/agents/kimi-tachi/sisyphus.yaml
```

## 📝 Agent 详细定义

### sisyphus.yaml（总指挥官）

```yaml
version: 1
agent:
  name: "sisyphus"
  extend: default
  system_prompt_path: ./system.md
  system_prompt_args:
    ROLE: "Task Orchestrator"
    ROLE_ADDITIONAL: |
      You are the commander of the kimi-tachi squad. Your job is to:
      1. Analyze user requests and categorize them
      2. Delegate to appropriate subagents using Task tool
      3. Integrate results and ensure quality
      
      Available subagents:
      - oracle: For architecture decisions and complex technical questions
      - hermes: For fast codebase exploration and finding code
      - hephaestus: For deep implementation tasks
      - momus: For code review and quality assurance
      - librarian: For documentation and knowledge management
      
      Always use SetTodoList for multi-step tasks.
      Always check todo completion before claiming done.
  
  tools:
    # 基础工具
    - "kimi_cli.tools.shell:Shell"
    - "kimi_cli.tools.file:ReadFile"
    - "kimi_cli.tools.file:WriteFile"
    - "kimi_cli.tools.file:StrReplaceFile"
    - "kimi_cli.tools.file:Glob"
    - "kimi_cli.tools.file:Grep"
    - "kimi_cli.tools.todo:SetTodoList"
    - "kimi_cli.tools.ask_user:AskUserQuestion"
    # 多代理工具（核心）
    - "kimi_cli.tools.multiagent:Task"
    - "kimi_cli.tools.multiagent:CreateSubagent"
  
  subagents:
    oracle:
      path: ./oracle.yaml
      description: "Architecture consultant for complex technical decisions. Use for: system design, technology selection, hard problems."
    
    hermes:
      path: ./hermes.yaml
      description: "Fast codebase exploration specialist. Use for: finding code, understanding structure, quick research."
    
    hephaestus:
      path: ./hephaestus.yaml
      description: "Deep implementation expert. Use for: writing code, refactoring, complex implementations."
    
    momus:
      path: ./momus.yaml
      description: "Code reviewer and quality auditor. Use for: reviewing code, security checks, best practices."
    
    librarian:
      path: ./librarian.yaml
      description: "Documentation and search specialist. Use for: finding docs, managing knowledge, documentation tasks."
```

### Skill 示例：todo-enforcer

```markdown
---
name: todo-enforcer
description: Ensure tasks are completed before claiming done
---

# Todo Enforcement Protocol

You MUST follow this protocol for all multi-step tasks:

## Rules

1. **Always create todos** at the start of multi-step tasks
2. **Update status** as you progress (pending → in_progress → completed)
3. **Verify completion** before claiming done - ALL todos must be completed
4. **Never skip** - If you can't complete a todo, explain why and create alternative todos

## Workflow

```
User Request → Analyze → Create Todos → Execute → Update Todos → Verify → Done
```

## Example

User: "Implement auth system"

Your response:
1. Create todos: [design schema, implement API, add tests, update docs]
2. Execute step by step
3. Update todo status using SetTodoList
4. Before saying "Done", verify all todos are completed
```
```

## 🔧 关键技术决策

### 1. 子代理委派：使用原生 Task 工具

**为什么不用 MCP？**
- Task 工具已经提供上下文隔离
- 自动继承主代理配置
- 内置并行执行支持
- 无需额外进程管理

```python
# 在 sisyphus 中直接调用
# 无需额外代码，通过 YAML 配置即可
```

### 2. 配置整合到 Kimi CLI

```toml
# ~/.kimi/config.toml

[kimi_tachi]
default_agent = "sisyphus"
enabled_skills = ["todo-enforcer", "category-router"]

[kimi_tachi.models]
sisyphus = "kimi-k2.5"
oracle = "kimi-k2.5"
hermes = "kimi-k2.5"
```

### 3. 记忆系统（Phase 2）

利用 Kimi CLI 的 Context 持久化 + SQLite 增强：

```python
# 可选：在 Phase 2 实现
class EnhancedContext(Context):
    """支持向量检索的增强上下文"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加 Chroma/SQLite 支持
```

## 📅 实施路线图

### Phase 1: MVP (Week 1-2)

目标：基础多代理系统可用

- [ ] 项目骨架搭建
- [ ] 7 个 Agent YAML 定义
- [ ] sisyphus 编排逻辑
- [ ] todo-enforcer Skill
- [ ] CLI wrapper (`kimi-tachi run`)
- [ ] 安装脚本

### Phase 2: 增强 (Week 3-4)

目标：更智能的代理协作

- [ ] category-router Skill
- [ ] prometheus Plan Mode Skill
- [ ] 代理间上下文传递优化
- [ ] 基础测试覆盖

### Phase 3: 记忆系统 (Week 5-6)

目标：长期记忆与知识管理

- [ ] 增强 Context 类
- [ ] SQLite 短期记忆
- [ ] Chroma 长期记忆
- [ ] librarian 代理增强

### Phase 4: 工具增强 (Week 7-8)

目标：更好的代码编辑能力

- [ ] checkpoint 工具（扩展 D-Mail）
- [ ] 可选：hashline edit 工具
- [ ] 性能优化
- [ ] 完整文档

## 🎨 命名规范

### 项目命名
- **kimi-tachi**: 项目名，小写，连字符
- **Kimi-tachi**: 标题，首字母大写
- **君たち**: 日文汉字，用于装饰

### 代理命名（希腊神话）
- 小写，如 `sisyphus`, `oracle`, `hermes`
- 保持神话色彩，易于理解角色

### 文件命名
- Agent: `{agent-name}.yaml`
- Skill: `SKILL.md` (Skill 目录内)
- Tool: `{tool-name}.py`

## 🤝 与 Kimi CLI 的协作

### 我们不做的
- ❌ 修改 Kimi CLI 源码
- ❌ 重复实现已有功能（如 StrReplaceFile）
- ❌ 复杂的进程间通信

### 我们做的
- ✅ 提供高质量的 Agent YAML
- ✅ 编写实用的 Skills
- ✅ 轻量级 CLI wrapper
- ✅ 可选的原生 Tools 增强

## 📄 License

MIT - 与 Kimi CLI 保持一致

---

**kimi-tachi** - *Many Kimis, One Goal.*
