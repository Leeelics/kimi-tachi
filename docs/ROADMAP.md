# kimi-tachi Roadmap

> **核心理念**：将软件工程问题转化为动漫角色分工问题
> 
> 最后更新: 2026-04-07

---

## 🎭 愿景与方向

### 为什么用动漫角色？

1. **性格即策略**：每个角色代表一种解决策略
   - 釜爺(kamaji) = 协调 · 总接口
   - 山兽神(shishigami) = 沉思 · 架构设计  
   - 猫巴士(nekobasu) = 速度 · 代码探索
   - 火魔(calcifer) = 实现 · 代码构建
   - 阎魔王(enma) = 审查 · 质量保证
   - 黄昏(tasogare) = 规划 · 任务分析
   - 火之鸟(phoenix) = 记忆 · 知识管理

2. **情感共鸣**：比冷冰冰的 "executor", "planner" 更生动

3. **团队感**：就像动画里的团队冒险，各司其职

```
    宫崎骏 (4/7)          新海诚 (1/7)     手冢治虫 (1/7)     鸟山明 (1/7)
         │                    │                │               │
    ┌────┴────┐              │                │               │
    ▼    ▼    ▼              ▼                ▼               ▼
 kamaji  shishigami  nekobasu  calcifer   tasogare       phoenix      enma
  (釜爺)   (山兽神)   (猫巴士)   (火魔)      (黄昏)        (火之鸟)    (阎魔王)
    │        │          │         │          │             │           │
 协调者   架构师    侦察兵    工匠      规划师        图书管理员    审查员
```

---

## ✅ 已完成

### Multi-Team Support (v0.7.0) ✅
- [x] TeamManager - 团队隔离和管理中心
- [x] Agent 重组 - coding / content 团队
- [x] CLI 团队管理命令 - `teams list/switch/info`
- [x] Team-scoped memory - 团队隔离记忆
- [x] 动态团队切换 - 运行时切换团队

### Phase 2: 架构优化 ✅
- [x] Dynamic Agent 创建 - MCP 进程 7→2
- [x] 消息总线架构 - 延迟 <100ms
- [x] 并行 Workflow 执行 - ≥40% 并行率
- [x] 上下文缓存优化 - ≥80% 命中率

### Memory System ✅
- [x] TachiMemory v3 - 智能 Session 探查
- [x] DecisionDeduplicator - 决策去重
- [x] MemNexus 集成 - 存储后端
- [x] Hooks 自动记忆 - SessionStart/PreCompact

---

## 📊 现状分析

### kimi-cli 关键发现

通过深入分析 `/home/lee/kit/kimi-cli` 源码，我们识别出以下关键信息：

#### 1. MCP 问题根源

```python
# agent.py:301-307 - 问题的根本原因
for subagent_name, subagent_spec in agent_spec.subagents.items():
    subagent = await load_agent(
        subagent_spec.path,
        runtime.copy_for_fixed_subagent(),
        mcp_configs=mcp_configs,  # ← 同样的配置传递给每个 subagent
        start_mcp_loading=start_mcp_loading,
        _restore_dynamic_subagents=False,
    )
```

**结论**: 每个 fixed subagent 都会独立启动 MCP 进程。这是 kimi-cli 的当前行为，短期内难以改变。

#### 2. kimi-cli 最新能力（v1.24.0+）

| 功能 | 版本 | kimi-tachi 可利用性 | 说明 |
|------|------|---------------------|------|
| **Plan Mode** | 1.19+ | ⭐⭐⭐ 高 | 可替代 tasogare 的规划阶段，支持多选项方案 |
| **Background Bash** | 1.23+ | ⭐⭐⭐ 高 | 长任务不阻塞，自动通知完成 |
| **MCP 延迟加载** | 1.24+ | ⭐⭐ 中 | 缓解启动慢问题，异步初始化 |
| **AskUserQuestion** | 1.14+ | ⭐⭐⭐ 高 | 结构化用户交互 |
| **Session 持久化** | 1.14+ | ⭐⭐⭐ 高 | 动态 subagent 可恢复 |
| **Context Compaction** | - | ⭐⭐⭐ 高 | 自动上下文压缩 |

### hello-agents 关键洞察

通过分析 [hello-agents](https://github.com/datawhalechina/hello-agents) 项目，我们获得以下核心启示：

#### 1. Skill 三级分层架构（核心抽象）

```
┌─────────────────────────────────────────┐
│ L1: Metadata                            │
│     始终加载 (~100 词)                   │
│     → AI 判断是否激活该技能              │
├─────────────────────────────────────────┤
│ L2: SKILL.md body                       │
│     触发后加载 (< 5k 词)                 │
│     → 具体操作指令                       │
├─────────────────────────────────────────┤
│ L3: Bundled resources                   │
│     按需加载 (无上限)                     │
│     - scripts/: 确定性脚本               │
│     - references/: 参考资料              │
│     - assets/: 产出物模板                │
└─────────────────────────────────────────┘
```

**关键原则**: Scripts 执行而不读入，零 token 成本

#### 2. 自由度光谱设计

| 自由度 | 实现方式 | 适用场景 | kimi-tachi 应用 |
|--------|----------|----------|-----------------|
| **高** | 文字指令 | 创造性任务 | tasogare（规划） |
| **中** | 伪代码/带参数脚本 | 有最佳实践但允许变通 | shishigami（架构） |
| **低** | 具体脚本、少量参数 | 脆弱操作 | calcifer（代码生成） |

#### 3. 多 Agent 协作模式

| 模式 | 特点 | kimi-tachi 适用性 |
|------|------|-------------------|
| **对话驱动** (AutoGen) | 自然语言协商 | ⭐⭐⭐ 当前设计 |
| **消息驱动** (AgentScope) | MsgHub 解耦通信 | ⭐⭐⭐ 优化方向 |
| **角色扮演** (CAMEL) | Inception Prompting | ⭐⭐ 人设增强 |
| **状态机驱动** (LangGraph) | 图结构控制 | ⭐⭐ workflow 模式 |

#### 4. 反模式清单（Anti-Patterns）

> **给 AI 写指令，而不是给人写文档**

用"不要做什么"代替正面描述，统一使用祈使语气：

```markdown
## 不要这样做

| 反模式 | 症状 | 修正方式 |
|--------|------|----------|
| 响应过长 | 超过 500 字 | 精简到核心要点 |
| 缺少代码示例 | 纯文字描述 | 每个概念配代码 |
```

---

## 🗺️ 迭代路线图

### Phase 0: Skill 架构升级（2-3 周）【前置阶段】

**目标**: 建立 Skill 三级分层架构，优化提示词工程

#### 0.1 Skill 结构重构

```
skills/
└── example/
    ├── SKILL.md              # L2: 指令（精简）
    ├── scripts/              # L3: 确定性脚本
    │   └── generate.py
    └── references/           # L3: 参考资料
        └── best-practices.md
```

**具体行动**:
- [ ] 设计 Skill 目录新标准（三级分层）
- [ ] 重构现有 skills（todo-enforcer, category-router）
- [ ] 创建 Skill 模板和开发指南
- [ ] 更新 AGENTS.md 中的 Skill 开发规范

#### 0.2 Agent 提示词优化

**应用自由度光谱设计**:

| Agent | 自由度 | 优化方向 |
|-------|--------|----------|
| **tasogare** | 高 | 增加创造性指令，减少约束 |
| **shishigami** | 中 | 提供架构模式选项，允许变通 |
| **calcifer** | 低 | 提供代码生成脚本，锁定风格 |
| **enma** | 中 | 提供检查清单，标准化审查 |

**引入反模式清单**:

```markdown
## kamaji 的反模式清单

| 反模式 | 症状 | 修正方式 |
|--------|------|----------|
| 直接暴露子 Agent 输出 | 用户看到原始 JSON | 必须整合后输出 |
| 跳过 Credits 部分 | 忘记致谢工作人员 | 每次响应必须包含 |
```

**具体行动**:
- [ ] 为每个 Agent 编写反模式清单
- [ ] 优化 system prompt 为祈使语气
- [ ] 测试优化后的 Agent 表现

**里程碑**: v0.1.5 - Skill 架构升级版

---

### Phase 1: 适配与稳定（4-6 周）

**目标**: 解决 MCP 问题，适配 kimi-cli 最新能力

#### 1.1 MCP 问题 Workaround

```
┌─────────────────────────────────────────────────────────────┐
│  方案评估                                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ A. 禁用 MCP  │  │ B. 动态创建  │  │ C. 等待上游  │         │
│  │  (简单可靠)  │  │  (灵活复杂)  │  │  (风险未知)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  推荐策略: 方案 A + B 的混合                                 │
│                                                             │
│  1. 默认 Agent 配置中移除 MCP 依赖                          │
│  2. 需要 MCP 时通过动态创建 (CreateSubagent) 实现            │
│  3. 文档中明确说明 MCP 使用建议                             │
└─────────────────────────────────────────────────────────────┘
```

**具体行动**:
- [ ] 修改 `kamaji.yaml`，移除或最小化 MCP 相关配置
- [ ] 更新 `agents/*.yaml`，确保 subagent 不重复加载 MCP
- [ ] 在文档中添加 MCP 使用注意事项

#### 1.2 Plan Mode 集成

利用 kimi-cli 原生的 Plan Mode 优化编排流程：

```
当前流程:                        优化后流程:
                                
tasogare 规划 ──→ 执行          kamaji 分析
                      ┌──────────────┴──────────────┐
                      ▼                              ▼
               简单任务                    复杂任务
               (直接处理)                  EnterPlanMode
                                                 │
                                                 ▼
                                          tasogare 生成计划
                                                 │
                                                 ▼
                                          ExitPlanMode
                                          (多选项呈现)
                                                 │
                                                 ▼
                                          用户选择方案
                                                 │
                                                 ▼
                                          calcifer/enma 执行
```

**具体行动**:
- [ ] 更新 `kamaji.yaml` system prompt，加入 Plan Mode 触发逻辑
- [ ] 测试复杂任务的 Plan Mode 自动触发
- [ ] 优化 `tasogare.yaml`，专注于计划生成

#### 1.3 Background Bash 集成

```
使用场景:
┌────────────────────────────────────────┐
│ calcifer 实现代码                      │
│         │                              │
│         ▼                              │
│  启动后台构建/测试 (run_in_background)  │
│         │                              │
│         ▼                              │
│  kamaji 继续其他工作                   │
│         │                              │
│         ▼                              │
│  自动通知任务完成                      │
└────────────────────────────────────────┘
```

**具体行动**:
- [ ] 更新 `calcifer.yaml`，加入后台任务指导
- [ ] 测试长构建任务的异步执行
- [ ] 更新文档说明 Background Bash 使用方式

**里程碑**: v0.2.0 - CLI v1.24+ 适配版

---

### Phase 2: 架构优化 ✅（已完成）

**目标**: 重构 Agent 层级，引入消息驱动架构

#### 2.1 Dynamic Agent 创建 ✅

```
优化设计:
  kamaji (fixed, 轻量)
    └── 使用 CreateSubagent 动态创建临时角色
    
结果: MCP 进程从 7 个减少到 ≤2 个
```

**已完成**: v0.4.0 - Labor Market 集成，七人衆注册为 built-in subagent types

#### 2.2 消息总线架构 ✅

**已完成**: 
- MessageBus 核心实现（Pydantic 模型、SQLite 持久化）
- 分布式追踪（Tracing）
- 点对点/广播/组播/发布订阅
- 延迟 <100ms

#### 2.3 并行 Workflow ✅

**已完成**:
- TaskDependencyAnalyzer（依赖分析）
- ParallelScheduler（并行调度）
- 语义/文件/显式依赖分析

#### 2.4 上下文缓存优化 ✅

**已完成**:
- FileContentCache（文件内容缓存）
- SemanticIndex（语义索引）
- ContextCompressor（上下文压缩）
- 命中率 ≥80%

---

### Phase 3: 团队与扩展 ✅（已完成）

**目标**: 支持多团队架构，扩展 agent 生态

#### 3.1 Multi-Team 架构 ✅

```
团队结构:
agents/
├── teams.yaml              # 团队配置
├── coding/                 # 编程团队
│   ├── kamaji.yaml         # 协调者
│   ├── nekobasu.yaml       # 侦察
│   ├── calcifer.yaml       # 实现
│   ├── shishigami.yaml     # 架构
│   ├── enma.yaml           # 审查
│   ├── tasogare.yaml       # 规划
│   └── phoenix.yaml        # 记忆
└── content/                # 内容团队
    └── ...                 # 内容创作角色
```

**核心组件**:
- `TeamManager` - 团队切换和管理
- `Team` - 团队定义（名称、主题、协调者）
- `ResolvedAgent` - 团队内 agent 解析

**CLI 支持**:
```bash
kimi-tachi teams list          # 列出所有团队
kimi-tachi teams switch <id>   # 切换团队
kimi-tachi teams info [id]     # 查看团队详情
kimi-tachi teams current       # 显示当前团队
```

**已完成**: v0.7.0

---

### Phase 4: 记忆与智能（进行中）

**目标**: 强化记忆系统，实现真正的智能体

#### 4.1 三层记忆系统

```
记忆架构:
┌─────────────────────────────────────────┐
│  Working Memory (工作记忆)               │
│  - 当前会话上下文                        │
│  - 短期决策缓存                          │
├─────────────────────────────────────────┤
│  Episodic Memory (情景记忆)              │
│  - 历史会话记录                          │
│  - 任务执行经验                          │
├─────────────────────────────────────────┤
│  Semantic Memory (语义记忆)              │
│  - 代码库知识                            │
│  - 跨项目经验                            │
└─────────────────────────────────────────┘
```

**目标指标**:
| 指标 | 当前 | 目标 |
|------|------|------|
| Working Memory 命中率 | 80% | ≥90% |
| Episodic Memory 检索准确率 | 70% | ≥80% |
| Semantic Memory 代码库覆盖率 | 60% | ≥70% |

#### 4.2 任务路由智能

```python
# 目标: 自动任务分类和路由

class TaskRouter:
    def route(self, task: str) -> AgentChain:
        # 语义理解任务类型
        # 自动选择最佳角色组合
        # 动态调整执行策略
```

**工作流程**:
```
用户输入任务
     ↓
[TaskRouter] 分析任务类型
     ↓
选择 Workflow 模板
     ↓
动态分配角色执行
     ↓
结果整合返回
```

#### 4.3 长期学习

- [ ] Agent 执行策略自优化
- [ ] 用户偏好学习
- [ ] 跨项目知识迁移
- [ ] 失败模式识别与规避

**里程碑**: v0.7.0 - 多团队架构版

---

### Phase 5: 生态建设（未来）

**目标**: 构建 Skills 生态，支持自定义角色

#### 4.1 Skills 扩展（基于三级分层架构）

```
skills/
├── dev/                          # 开发相关
│   ├── code-generator/           # 代码生成
│   │   ├── SKILL.md              # L2: 指令
│   │   └── scripts/              # L3: 确定性脚本
│   │       └── generate.py
│   ├── test-writer/              # 测试编写
│   ├── doc-generator/            # 文档生成
│   └── api-client/               # API 客户端生成
│
├── review/                       # 代码审查
│   ├── security-check/           # 安全检查
│   ├── performance/              # 性能分析
│   └── style-check/              # 代码风格
│
├── project/                      # 项目管理
│   ├── onboarding/               # 新成员引导
│   ├── release/                  # 发布助手
│   └── changelog/                # 变更日志
│
└── anime/                        # 动漫角色（示例）
    ├── ghibli-style/             # 吉卜力风格建议
    └── character-voice/          # 角色语气转换
```

#### 4.2 自定义角色系统

```yaml
# 示例: 用户自定义角色模板
custom_agent_template:
  name: "my-agent"
  base_role: "calcifer"        # 继承火魔的基础能力
  
  customization:
    system_prompt_additions: |
      你专注于前端开发，擅长 React 和 TypeScript。
      你重视组件的可复用性和可访问性。
    
    # 反模式清单（新增）
    anti_patterns: |
      | 反模式 | 症状 | 修正方式 |
      | 忽略 TypeScript 类型 | any 滥用 | 强制类型定义 |
    
    skills:                      # 关联的 skills
      - "dev/code-generator"
      - "review/style-check"
    
    tools_priority:              # 工具使用偏好
      high: ["Glob", "Grep", "StrReplaceFile"]
      low: ["Shell"]
    
    # 自由度设置（新增）
    freedom_level: "medium"      # high/medium/low
```

#### 4.3 社区与分享

```
社区生态:
├── 角色市场
│   ├── 官方角色 (7人衆)
│   ├── 社区角色
│   └── 企业定制
│
├── Skills 仓库
│   ├── 官方维护
│   └── 社区贡献
│
└── 配置分享
    ├── .kimi-tachi/config.yaml 模板
    └── 项目最佳实践
```

**具体行动**:
- [ ] 开发 5+ 实用 Skills
- [ ] 设计自定义角色模板系统
- [ ] 建立社区分享机制
- [ ] 编写角色开发指南

**里程碑**: v1.0.0 - 生态完整版

---

## 📈 成功指标

| 阶段 | 指标 | 目标值 | 当前 |
|------|------|--------|------|
| **Phase 2** | MCP 进程数 | ≤ 2 | ✅ ≤2 |
| **Phase 2** | 消息总线延迟 | < 100ms | ✅ <100ms |
| **Phase 2** | 并行执行比例 | ≥ 40% | ✅ ≥40% |
| **Phase 2** | 上下文缓存命中率 | ≥ 80% | ✅ ≥80% |
| **Phase 3** | 团队切换响应时间 | < 500ms | ✅ <500ms |
| **Phase 3** | 团队配置可扩展性 | ≥ 5 团队 | ✅ 支持 |
| **Phase 4** | Working Memory 命中率 | ≥ 90% | 🔄 进行中 |
| **Phase 4** | 任务路由准确率 | ≥ 85% | 📋 待开始 |
| **Phase 5** | Skills 数量 | ≥ 10 | 📋 待开始 |
| **Phase 5** | 社区贡献角色 | ≥ 5 | 📋 待开始 |

---

## 🔗 相关文档

- [anti-patterns.md](./anti-patterns.md) - 反模式清单
- [memory.md](./memory.md) - 记忆系统文档
- [hooks.md](./hooks.md) - Hooks 集成指南
- [contributing.md](./contributing.md) - 贡献指南
- [hello-agents](https://github.com/datawhalechina/hello-agents) - 智能体系统最佳实践参考

---

*「七人の力が一つになれば、どんな敵にも負けない。」*
*（七人的力量合为一体，任何敌人都无法战胜。）*
