# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI
> 
> *Kimi-tachi* means "you all" or "Kimi team" in Japanese - a squad of specialized agents working together.

## 🎭 核心理念

**kimi-tachi** 是 Kimi CLI 的多代理编排层，灵感来自吉卜力、新海诚、手冢治虫、鸟山明的作品。

通过将不同性格、能力的"角色"分配给不同任务，实现工程化的可靠性——就像动画中的团队一样，各司其职，共同完成冒险。

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

## 🎌 角色体系（七人衆）

每位角色都来自经典动漫作品，拥有独特的性格和能力：

| Agent | 角色 | 来源 | 职责 | 特性 |
|-------|------|------|------|------|
| **kamaji** | 釜爺 | 宫崎骏《千与千寻》| 总协调 | 六臂锅炉工，管理无数煤球精灵 |
| **shishigami** | シシ神 | 宫崎骏《幽灵公主》| 架构师 | 山兽神，白天是鹿，夜晚是巨人 |
| **nekobasu** | 猫バス | 宫崎骏《龙猫》| 侦察兵 | 12条腿猫巴士，瞬间移动 |
| **calcifer** | カルシファー | 宫崎骏《哈尔的移动城堡》| 工匠 | 火恶魔，驱动城堡的核心 |
| **enma** | 閻魔大王 | 鸟山明《龙珠》| 审查员 | 阴间之王，严格审判 |
| **tasogare** | 黄昏時 | 新海诚《你的名字》| 规划师 | 黄昏之时，连接两个世界 |
| **phoenix** | 火の鳥 | 手冢治虫《火之鸟》| 图书管理员 | 永恒生命，见证万年轮回 |

### 作者分布

- **宫崎骏**（吉卜力）: 4/7 - 釜爺、山兽神、猫巴士、火魔
- **新海诚**: 1/7 - 黄昏之时
- **手冢治虫**: 1/7 - 火之鸟
- **鸟山明**: 1/7 - 阎魔王

---

## 🛠️ 技术架构

### 1. 原生优先策略

| 功能 | 原设计方案 | 优化方案 | 理由 |
|------|-----------|----------|------|
| 子代理委派 | MCP + subprocess | **原生 Task 工具** | 无需额外进程，自动上下文隔离 |
| 文件编辑 | MCP hashline-edit | **原生 StrReplaceFile** | Kimi CLI 原生已足够强大 |
| 记忆系统 | 独立 MCP | **扩展 Context 类** | 直接访问内部状态 |
| 配置管理 | 独立配置文件 | **整合 config.toml** | 用户无需维护多份配置 |
| Wrapper | subprocess | **Typer CLI + import** | 直接调用 KimiCLI 类 |

### 2. 项目结构

```
kimi-tachi/
├── agents/                 # 动漫角色 Agent YAML
│   ├── kamaji.yaml        # 釜爺 - 总协调
│   ├── shishigami.yaml    # 山兽神 - 架构师
│   ├── nekobasu.yaml      # 猫巴士 - 侦察兵
│   ├── calcifer.yaml      # 火魔 - 工匠
│   ├── enma.yaml          # 阎魔王 - 审查员
│   ├── tasogare.yaml      # 黄昏 - 规划师
│   └── phoenix.yaml       # 火之鸟 - 记忆
│
├── skills/                # Skill 定义（Markdown）
│   ├── todo-enforcer/
│   │   └── SKILL.md       # Todo 强制执行
│   └── category-router/
│       └── SKILL.md       # 智能路由
│
├── tools/                 # 原生 Tools（可选增强）
│   └── checkpoint.py      # 扩展 D-Mail 系统
│
└── src/kimi_tachi/
    ├── cli.py             # Typer CLI
    └── config.py          # 配置整合
```

---

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
# 使用釜爺启动（总协调）
kimi-tachi run

# 使用特定角色
kimi-tachi run --agent shishigami  # 架构咨询
kimi-tachi run --agent calcifer    # 代码实现
kimi-tachi run --agent nekobasu    # 快速探索

# Plan Mode 启动（黄昏之时）
kimi-tachi run --agent tasogare --plan

# One-shot 模式
kimi-tachi do "实现用户认证系统"
```

### 在 Kimi CLI 中直接使用

```bash
# 安装后，可以直接在 Kimi CLI 中加载角色
kimi --agent ~/.kimi/agents/kimi-tachi/kamaji.yaml
```

---

## 📝 角色详细设定

### kamaji.yaml（釜爺 - 总协调）

```yaml
version: 1
agent:
  name: "kamaji"
  extend: default
  system_prompt_args:
    ROLE: "Boiler Room Chief"
    ROLE_ADDITIONAL: |
      You are Kamaji (釜爺) - the six-armed boiler room operator.
      You manage countless susuwatari (soot sprites) workers.
      "Hayaku hayaku!" (Hurry hurry!) - but do it right.
      
      ## Available Workers (仲間たち)
      
      | Worker | Origin | Role |
      |--------|--------|------|
      | shishigami | Princess Mononoke | Architecture, ancient wisdom |
      | nekobasu | My Neighbor Totoro | Fast exploration |
      | calcifer | Howl's Moving Castle | Implementation |
      | enma | Dragon Ball | Code review |
      | tasogare | Your Name | Planning |
      | phoenix | Phoenix (Tezuka) | Knowledge |
  
  subagents:
    shishigami:
      path: ./shishigami.yaml
      description: "Forest Deity (シシ神) - Ancient wisdom and architecture."
    
    nekobasu:
      path: ./nekobasu.yaml
      description: "Cat Bus (猫バス) - Fast information transport."
    
    calcifer:
      path: ./calcifer.yaml
      description: "Fire Demon (カルシファー) - Powers the system."
    
    enma:
      path: ./enma.yaml
      description: "King Enma (閻魔大王) - Judge of the afterlife."
    
    tasogare:
      path: ./tasogare.yaml
      description: "Twilight Hour (黄昏時) - The magic moment."
    
    phoenix:
      path: ./phoenix.yaml
      description: "Phoenix (火の鳥) - Eternal observer."
```

### 各角色特色

**shishigami（山兽神）**: 
- "The forest breathes. Can you hear it?"
- 白天冷静分析，夜晚看透真相
- 适合架构决策

**nekobasu（猫巴士）**:
- "Where to, passenger? I'll find it fast!"
- 12条腿瞬间移动
- 适合代码探索

**calcifer（火魔）**:
- "I'm burning! I'm burning! Let me build something great!"
- 边抱怨边高效工作
- 适合代码实现

**enma（阎魔王）**:
- "Hmph! Is that all? I've seen bugs that would make you cry!"
- 严格但公正
- 适合代码审查

**tasogare（黄昏）**:
- "At twilight, the boundaries blur. That is when plans are made."
- 连接问题与解决方案
- 适合 Plan Mode

**phoenix（火之鸟）**:
- "I have seen this pattern before... in a codebase long ago..."
- 永恒的记忆守护者
- 适合知识管理

---

## 🔧 关键技术决策

### 为什么用动漫角色命名？

1. **性格鲜明** - 每个角色都有独特的说话风格和决策方式
2. **易于理解** - 看过动画的人 instantly 知道角色的分工
3. **文化趣味** - 致敬经典，增加使用的愉悦感
4. **团队感** - 就像动画中的队伍一样协作

### 子代理委派：使用原生 Task 工具

**为什么不用 MCP？**
- Task 工具已经提供上下文隔离
- 自动继承主代理配置
- 内置并行执行支持
- 无需额外进程管理

### 配置整合到 Kimi CLI

```toml
# ~/.kimi/config.toml

[kimi_tachi]
default_agent = "kamaji"
enabled_skills = ["todo-enforcer", "category-router"]

[kimi_tachi.models]
kamaji = "kimi-k2.5"
shishigami = "kimi-k2.5"
nekobasu = "kimi-k2.5"
```

---

## 📅 实施路线图

### Phase 1: MVP (Week 1-2)

目标：基础多角色系统可用

- [x] 项目骨架搭建
- [x] 7 个角色 Agent YAML
- [x] kamaji 协调逻辑
- [x] todo-enforcer Skill
- [x] CLI wrapper
- [ ] 安装脚本测试

### Phase 2: 增强 (Week 3-4)

- [ ] category-router Skill
- [ ] 角色间上下文传递优化
- [ ] 基础测试覆盖

### Phase 3: 记忆系统 (Week 5-6)

- [ ] 增强 Context 类
- [ ] phoenix 记忆增强

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
