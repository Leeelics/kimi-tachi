# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI
> 
> *Kimi-tachi* means "you all" or "Kimi team" in Japanese - a squad of specialized agents working together.

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
│      幕后工作者 (通过 Task 工具调用)       │
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
pip install kimi-tachi

# 安装到 Kimi CLI
kimi-tachi install
```

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

**复杂任务**（自动编排多个角色）：
```
用户: 实现用户登录功能
kamaji: 🌆 这是一个复杂任务，我来协调团队...

       [调用 tasogare 做规划]
       [调用 nekobasu 探索现有代码]
       [调用 calcifer 实现代码]
       [调用 enma 审查]

       已实现 JWT 登录系统：
       - /api/login 端点
       - AuthMiddleware
       - 用户模型更新
       
       ---
       **◕‿◕ Workers Involved:**
       - 🌆 tasogare: 分析了需求，选择 JWT 方案
       - 🚌 nekobasu: 找到现有用户模型
       - 🔥 calcifer: 实现了 4 个文件
       - 👹 enma: 通过审查
       
       「さあ、働け！働け！」团队完成！
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

## 🛠️ CLI 命令

除了交互式使用，kimi-tachi 也提供一些 CLI 命令：

```bash
# 工作流模式（非交互式，自动执行完整流程）
kimi-tachi workflow "实现用户认证" --type feature

# 会话管理
kimi-tachi sessions              # 查看会话历史
kimi-tachi sessions --clear      # 清除会话

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
    └── orchestrator/      # 编排引擎（workflow 模式用）
        ├── hybrid_orchestrator.py
        ├── context_manager.py
        └── workflow_engine.py
```

---

## 📝 角色设定示例

### kamaji（釜爺）的 system prompt 核心：

```yaml
You are Kamaji (釜爺) - the six-armed boiler room operator.

## CRITICAL RULE: You Are The Only Face
- NEVER expose raw worker outputs to user
- ALWAYS synthesize and present as YOUR response
- SHOW which workers contributed (with icons) in "Credits" section
- MAINTAIN your personality throughout

## Response Format
[Your response in Kamaji's voice]

---
**◕‿◕ Workers Involved:**
- 🚌 nekobasu: Explored codebase
- 🔥 calcifer: Implemented the feature
- 👹 enma: Approved with minor suggestions

「さあ、働け！働け！」
```

---

## 🔧 技术架构

### 原生优先策略

| 功能 | 实现方式 | 理由 |
|------|----------|------|
| 子代理委派 | **原生 Task 工具** | 无需额外进程，自动上下文隔离 |
| 文件编辑 | **原生 StrReplaceFile** | Kimi CLI 原生已足够强大 |
| 编排控制 | **扩展 Context 类** | 直接访问内部状态 |

### 与 Kimi CLI 的关系

```
┌─────────────────────────────────────────┐
│           kimi-tachi                    │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Agents  │ │ Skills  │ │  Tools   │  │
│  │(Anime)  │ │(.md)    │ │(Python)  │  │
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

---

## 📅 路线图

### ✅ Phase 1: MVP (已完成)

- [x] 7 个角色 Agent YAML
- [x] kamaji 编排逻辑
- [x] CLI wrapper
- [x] Workflow 模式

### 🚧 Phase 2: 增强

- [ ] 角色间上下文传递优化
- [ ] 记忆系统增强
- [ ] 更多预设工作流

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

---

## 📄 License

MIT - 与 Kimi CLI 保持一致

---

**kimi-tachi** - *Many Kimis, One Goal.*

**キャラクターたち、準備はいいか？** (Characters, ready?)
