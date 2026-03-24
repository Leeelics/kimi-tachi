# kimi-tachi (君たち) v0.4.0

> Multi-agent task orchestration for Kimi CLI
> 
> *Kimi-tachi* means "you all" or "Kimi team" in Japanese - a squad of specialized agents working together.

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## 🎉 v0.4.0 新特性

**充分利用 kimi-cli 1.25.0+ 新能力！**

- ✅ **Labor Market 集成** - 七人衆注册为 built-in subagent types
- ✅ **Agent Resume** - 跨会话上下文保留，智能复用 agent 实例
- ✅ **Background Tasks** - 长时间任务异步执行
- ✅ **WireAdapter** - 统一 Message Bus 和 Wire 通信
- ✅ **原生 Agent 工具** - 支持 coder/explore/plan + 七人衆角色
- ✅ **Plugin 系统** - 通过 `kimi plugin install` 安装

```bash
# 快速开始
pip install kimi-tachi
kimi plugin install agents/kimi-tachi
kimi-tachi start
```

---

## 🎭 核心理念

**kimi-tachi** 是 Kimi CLI 的多代理编排层，灵感来自吉卜力、新海诚、手冢治虫、鸟山明的作品。

**你只需要和 釜爺(kamaji) 对话**，其他的角色在幕后工作——就像动画中的团队一样，各司其职，共同完成冒险。

```
┌─────────────────────────────────────────┐
│              用户 (你)                   │
│                  │                      │
│                  ▼                      │
│           ┌───────────┐                 │
│           │  釜爺     │ ◄── 唯一接口     │
│           │ (kamaji)  │                 │
│           └─────┬─────┘                 │
│                 │                       │
│    ┌────────────┼────────────┐          │
│    ▼            ▼            ▼          │
│ ┌──────┐   ┌──────┐   ┌──────┐         │
│ │ 🚌   │   │ 🔥   │   │ 👹   │         │
│ │猫巴士 │   │ 火魔 │   │阎王 │  ...     │
│ └──────┘   └──────┘   └──────┘         │
│      幕后工作者 (通过 Agent 工具调用)      │
└─────────────────────────────────────────┘
```

---

## ◕‿◕ 角色体系（七人衆）

每位角色都来自经典动漫作品，拥有独特的性格和能力：

| Agent | 角色 | 来源 | 职责 | Emoji |
|-------|------|------|------|-------|
| **kamaji** | 釜爺 | 宫崎骏《千与千寻》| 总协调 | ◕‿◕ |
| **shishigami** | シシ神 | 宫崎骏《幽灵公主》| 架构师 | 🦌 |
| **nekobasu** | 猫バス | 宫崎骏《龙猫》| 侦察兵 | 🚌 |
| **calcifer** | カルシファー | 宫崎骏《哈尔的移动城堡》| 工匠 | 🔥 |
| **enma** | 閻魔大王 | 鸟山明《龙珠》| 审查员 | 👹 |
| **tasogare** | 黄昏時 | 新海诚《你的名字》| 规划师 | 🌆 |
| **phoenix** | 火の鳥 | 手冢治虫《火之鸟》| 图书管理员 | 🐦 |

### 作者分布

- **宫崎骏**（吉卜力）: 4/7 - 釜爺、山兽神、猫巴士、火魔
- **新海诚**: 1/7 - 黄昏之时
- **手冢治虫**: 1/7 - 火之鸟
- **鸟山明**: 1/7 - 阎魔王

---

## 🚀 使用方式

### 安装

```bash
# 1. 安装 Python 包
pip install kimi-tachi

# 2. 安装 kimi-cli plugin
kimi plugin install agents/kimi-tachi

# 3. 验证安装
kimi-tachi --version
kimi plugin list
```

**系统要求**: kimi-cli >=1.25.0, Python >=3.12

### 启动 kimi-tachi

```bash
# 直接启动（默认使用 kamaji）
kimi-tachi

# 或显式启动
kimi-tachi start
```

### 与 kamaji 对话

启动后，你只需要像平常一样和 kimi 对话。**kamaji 会自动判断是否需要调用其他角色**。

**简单任务**（kamaji 自己处理）：
```
用户: 读取 pyproject.toml
kamaji: [直接读取文件内容]
```

**需要探索的任务**（自动调用 🚌 猫巴士）：
```
用户: 找到所有和 auth 相关的代码
kamaji: 🚌 让我派猫巴士去找找...
       
       找到 5 个相关文件：
       - src/auth.py
       - src/middleware.py
       ...
       
       ---
       **◕‿◕ Workers Involved:**
       - 🚌 nekobasu: 探索了 src/ 目录，找到 5 个文件
```

**复杂任务**（自动编排多个角色，支持 Resume）：
```
用户: 实现用户登录功能
kamaji: 🌆 这是一个复杂任务，我来协调团队...

       [调用 tasogare 做规划]
       [调用 nekobasu 探索现有代码]
       → nekobasu agent_id: a1b2c3d4 (保留上下文)
       
       [调用 calcifer 实现代码]
       [调用 enma 审查]

       已实现 JWT 登录系统：
       - /api/login 端点
       - AuthMiddleware
       - 用户模型更新
       
       ---
       **◕‿◕ Workers Involved:**
       - 🌆 tasogare: 分析了需求，选择 JWT 方案
       - 🚌 nekobasu: 找到现有用户模型 (agent: a1b2c3d4)
       - 🔥 calcifer: 实现了 4 个文件
       - 👹 enma: 通过审查
       
       「さあ、働け！働け！」团队完成！

用户: 继续实现注册功能
kamaji: 🚌 复用 nekobasu (a1b2c3d4) 继续探索...
       
       [resume a1b2c3d4] 在已有上下文基础上继续工作
```

---

## 🎛️ 自动编排机制

kamaji 会根据任务复杂度自动决定工作方式：

| 复杂度 | 判断标准 | 工作方式 |
|--------|----------|----------|
| **简单** | 单文件、<10行、明确 | kamaji 直接处理 |
| **中等** | 多文件、需要上下文 | 🚌 探索 → 执行 |
| **复杂** | 新功能、架构决策 | 🌆 规划 + 🚌 探索 → 🦌 架构 → 🔥 实现 → 👹 审查 |

### 并行 vs 顺序

- **并行**：探索 + 规划（互不依赖）
- **顺序**：探索 → 架构 → 实现 → 审查（有依赖关系）

---

## ⚙️ 配置选项

### 环境变量

```bash
# v0.4.0: Agent 会话管理
export KIMI_TACHI_SESSION_ID="my-project"  # 会话 ID
export KIMI_TACHI_RESUME_TIMEOUT=1800      # Resume 超时（秒）

# Phase 2.1: 动态 Agent 创建（默认启用）
export KIMI_TACHI_DYNAMIC_AGENTS=true

# Phase 2.2: 消息总线（默认启用）
export KIMI_TACHI_MESSAGE_BUS_ENABLED=true

# Phase 2.4: 上下文缓存（默认启用）
export KIMI_TACHI_ENABLE_CACHE=true

# 调试模式
export KIMI_TACHI_DEBUG_AGENTS=true
```

### 代码中使用

```python
from kimi_tachi.orchestrator import HybridOrchestrator
from kimi_tachi.message_bus import MessageBus
from kimi_tachi.context import ContextCacheManager
from kimi_tachi.session import get_session_manager  # v0.4.0
from kimi_tachi.background import get_task_manager   # v0.4.0

# 完整功能启用
orch = HybridOrchestrator(
    enable_dynamic=True,   # Phase 2.1
    enable_cache=True,     # Phase 2.4
)

# v0.4.0: 会话管理 - 跟踪和复用 agent
session = get_session_manager("my-project")
if agent_id := session.should_resume("nekobasu"):
    # 复用现有 agent，保留上下文
    Agent(description="继续探索", prompt="...", subagent_type="nekobasu", resume=agent_id)

# v0.4.0: 后台任务 - 异步执行
 tasks = get_task_manager()
task = await tasks.start_task(
    agent_type="nekobasu",
    description="深度代码分析",
    prompt="分析整个代码库架构",
)

# 使用消息总线
bus = MessageBus()       # Phase 2.2

# 使用并行 Workflow
from kimi_tachi.orchestrator.workflow_engine import WorkflowEngine
engine = WorkflowEngine(orch, use_parallel=True)  # Phase 2.3
```

---

## 🛠️ CLI 命令

除了交互式使用，kimi-tachi 也提供一些 CLI 命令：

```bash
# 工作流模式（非交互式，自动执行完整流程）
kimi-tachi workflow "实现用户认证" --type feature

# v0.4.0: 后台任务管理
kimi-tachi tasks                 # 列出后台任务
kimi-tachi tasks --status active # 查看活跃任务

# 会话管理
kimi-tachi sessions              # 查看会话历史
kimi-tachi sessions --clear      # 清除会话

# 缓存管理
kimi-tachi cache stats           # 查看缓存统计
kimi-tachi cache clear           # 清空缓存

# 其他命令
kimi-tachi list-agents           # 列出所有角色
kimi-tachi status                # 检查安装状态
kimi-tachi install               # 安装/更新
kimi-tachi uninstall             # 卸载
```

---

## 📁 项目结构

```
kimi-tachi/
├── agents/                 # 动漫角色 Agent YAML
│   ├── kamaji.yaml        # ◕‿◕ 釜爺 - 总协调（唯一用户接口）
│   ├── shishigami.yaml    # 🦌 山兽神 - 架构师
│   ├── nekobasu.yaml      # 🚌 猫巴士 - 侦察兵
│   ├── calcifer.yaml      # 🔥 火魔 - 工匠
│   ├── enma.yaml          # 👹 阎魔王 - 审查员
│   ├── tasogare.yaml      # 🌆 黄昏 - 规划师
│   └── phoenix.yaml       # 🐦 火之鸟 - 记忆
│
├── skills/                # Skill 定义（Markdown）
│   ├── kimi-tachi/        # kimi-tachi 内部命令
│   ├── todo-enforcer/     # Todo 强制执行
│   └── category-router/   # 智能路由
│
└── src/kimi_tachi/
    ├── cli.py             # Typer CLI
    ├── session/           # v0.4.0: Agent 会话管理
    │   ├── agent_session.py
    │   └── __init__.py
    ├── background/        # v0.4.0: 后台任务管理
    │   ├── task_manager.py
    │   └── __init__.py
    ├── adapters/          # v0.4.0: Wire 桥接适配器
    │   ├── wire_adapter.py
    │   └── __init__.py
    ├── message_bus/       # Phase 2.2: 消息总线
    │   ├── models.py
    │   ├── hub.py
    │   ├── persistence.py
    │   └── tracing.py
    ├── context/           # Phase 2.4: 上下文缓存
    │   ├── file_cache.py
    │   ├── semantic_index.py
    │   ├── analysis_cache.py
    │   └── compressor.py
    └── orchestrator/      # 编排引擎
        ├── hybrid_orchestrator.py
        ├── agent_factory.py      # Phase 2.1
        ├── dependency_analyzer.py # Phase 2.3
        ├── parallel_scheduler.py  # Phase 2.3
        └── workflow_engine.py
```

---

## 🔧 技术架构

### v0.4.0 架构 (Labor Market + Agent Resume)

```
┌─────────────────────────────────────────────────────────────┐
│                    v0.4.0 混合架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Labor Market 集成                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  七人衆注册为 built-in types:                        │   │
│  │  nekobasu, calcifer, shishigami, enma, ...          │   │
│  │  Agent(subagent_type="nekobasu") 自动加载角色        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Agent Resume 机制                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Session Manager → 跟踪 agent 实例                   │   │
│  │  resume=agent_id → 复用上下文                       │   │
│  │  智能建议: should_resume(agent_type)                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Background Tasks                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  长时间任务异步执行                                  │   │
│  │  run_in_background=True                             │   │
│  │  TaskOutput / 自动通知                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  WireAdapter (Message Bus ↔ Wire)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  统一通信接口                                        │   │
│  │  本地/远程模式自动切换                               │   │
│  │  Agent 状态缓存                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### v0.4.0 通信策略

| 场景 | 机制 | 说明 |
|------|------|------|
| 同进程通信 | **Message Bus** | 内部协调，丰富消息模式 |
| 跨 Agent 通信 | **Agent Tool + Wire** | kimi-cli 原生机制 |
| Agent 复用 | **resume 参数** | 上下文自动保留 |
| 状态查询 | **SubagentStore** | 只读，快速 |
| 后台任务 | **run_in_background** | 异步执行 |

### 与 Kimi CLI 的关系

```
┌─────────────────────────────────────────┐
│           kimi-tachi v0.4.0             │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Agents  │ │ Skills  │ │  Tools   │  │
│  │(Anime)  │ │(.md)    │ │(Python)  │  │
│  └────┬────┘ └────┬────┘ └────┬─────┘  │
│       └─────────────┴───────────┘       │
│                   │                     │
│  ┌────────────────┼────────────────┐   │
│  │  Message Bus   │  WireAdapter   │   │
│  │  (内部协调)     │  (Agent 通信)   │   │
│  └────────────────┼────────────────┘   │
│                   │                     │
└───────────────────┼─────────────────────┘
                    │
┌───────────────────┼─────────────────────┐
│              Kimi CLI 1.25.0+           │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │  Agent  │ │  Wire   │ │Subagent  │  │
│  │  Tool   │ │         │ │  Store   │  │
│  └─────────┘ └─────────┘ └──────────┘  │
└─────────────────────────────────────────┘
```

---

## 📅 路线图

### ✅ Phase 1: MVP (v0.1.0)

- [x] 7 个角色 Agent YAML
- [x] kamaji 编排逻辑
- [x] CLI wrapper
- [x] Workflow 模式

### ✅ Phase 2: 架构优化 (v0.2.0)

- [x] **2.1** 动态 Agent 创建 - MCP 7→2
- [x] **2.2** 消息总线架构 - 延迟 <100ms
- [x] **2.3** Workflow 并行执行 - 并行 ≥40%
- [x] **2.4** 上下文缓存优化 - 命中率 ≥80%

### ✅ Phase 3: 系统集成 (v0.3.0)

- [x] Skills → Plugins 转换
- [x] 工作流追踪与可视化
- [x] kimi-cli 1.25.0+ 兼容

### ✅ Phase 4: Labor Market (v0.4.0) - 已完成！

- [x] **4.1** 七人衆注册为 built-in types
- [x] **4.2** Agent Resume 机制
- [x] **4.3** Background Tasks
- [x] **4.4** WireAdapter 桥接

### 🚧 Phase 5: 智能记忆 (v0.5.0)

- [ ] 跨会话长期记忆
- [ ] 知识图谱构建
- [ ] 个性化工作流学习

---

## 📊 性能指标

| 指标 | v0.1.0 | v0.2.0 | v0.4.0 | 提升 |
|------|--------|--------|--------|------|
| MCP 进程数 | 7 | ≤2 | ≤2 | 71% ↓ |
| 消息延迟 | ~500ms | <100ms | <100ms | 80% ↓ |
| 并行执行比例 | 0% | ≥40% | ≥40% | 新增 |
| 缓存命中率 | 0% | ≥80% | ≥80% | 新增 |
| Token 使用 | 100% | ~70% | ~50% | 50% ↓ |
| Agent 复用 | ❌ | ❌ | ✅ | 新增 |
| 后台任务 | ❌ | ❌ | ✅ | 新增 |

---

## 🤝 与 Kimi CLI 的协作

### 我们不做的
- ❌ 修改 Kimi CLI 源码
- ❌ 重复实现已有功能
- ❌ 复杂的进程间通信

### 我们做的
- ✅ 提供高质量的角色 Agent YAML
- ✅ 编写实用的 Skills
- ✅ 轻量级 CLI wrapper
- ✅ 架构优化（动态创建、消息总线、并行执行、上下文缓存）

---

## 📄 License

MIT - 与 Kimi CLI 保持一致

---

**kimi-tachi v0.4.0** - *Many Kimis, One Goal.*

**キャラクターたち、準備はいいか？** (Characters, ready?)

**「さあ、働け！働け！」** (Work! Work!)
