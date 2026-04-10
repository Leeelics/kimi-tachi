# kimi-tachi Roadmap

> **核心理念**：将软件工程问题转化为动漫角色分工问题
> 
> 最后更新: 2026-04-10

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

### Multi-Team Support (v0.7.0-v0.7.1) ✅
- [x] TeamManager - 团队隔离和管理中心
- [x] Agent 重组 - coding / content 团队
- [x] CLI 团队管理命令 - `teams list/switch/info/current`
- [x] Team-scoped memory - 团队隔离记忆
- [x] 动态团队切换 - 运行时切换团队
- [x] `install` 默认覆盖升级，`--skip-existing` 保留旧文件

### Phase 2: 架构优化 ✅
- [x] Dynamic Agent 创建 - MCP 进程 7→2
- [x] 消息总线架构 - 延迟 <100ms
- [x] 并行 Workflow 执行 - ≥40% 并行率
- [x] 上下文缓存优化 - ≥80% 命中率

### Memory System (基础版) ✅
- [x] TachiMemory v3 - 智能 Session 探查
- [x] DecisionDeduplicator - 决策去重
- [x] MemNexus 集成（接口层）- 存储后端
- [x] Hooks 自动记忆 - SessionStart/PreCompact

---

## 📊 现状分析

### v0.7.x 发布经验与教训

v0.7.0/0.7.1 的发布暴露了当前最紧迫的问题：

```
┌─────────────────────────────────────────────────────────────┐
│  问题                         影响          优先级          │
├─────────────────────────────────────────────────────────────┤
│  wheel install 路径解析       无法运行      🔴 高           │
│  CI validate job 缺少 uv      Release 失败  🔴 高           │
│  无 wheel 安装 E2E 测试       无法提前发现  🟡 中           │
│  PyPI 不可覆盖                发版即定版    🟡 中           │
│  TaskRouter 缺失              无自动编排    🔴 高           │
└─────────────────────────────────────────────────────────────┘
```

**关键结论**：架构代码已经就位，但 "最后一公里" 的稳定性、测试覆盖、以及真正的用户价值（智能任务路由）还没有完成。

### kimi-cli 关键发现

通过深入分析 kimi-cli 源码，我们识别出以下关键信息：

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

---

## 🗺️ 迭代路线图

### v0.8.0: 智能编排与稳定性（当前重点，4-6 周）

**目标**: 让 kimi-tachi 从 "团队启动器" 进化为 "任务编排器"，同时加固发布稳定性

v0.7.0/0.7.1 的发布教训：架构代码再漂亮，"最后一公里" 不稳，用户就用不上。因此 v0.8.0 将智能编排与稳定性硬化合并推进。

**目标**: 让 kimi-tachi 从 "团队启动器" 进化为 "任务编排器"

当前 `kimi-tachi` 只是启动 kamaji 并把任务交给它。v0.8.0 要让它能：
1. **理解任务类型** → 自动选择 team + workflow
2. **复杂任务进入 Plan Mode**
3. **后台任务自动异步化**

#### 8.1 稳定性加固（并行推进）

基于 v0.7.x 发布教训，必须完成的保底工作：

- [ ] **wheel install E2E 测试**
  - CI 中构建 wheel → `pip install` → 运行完整 CLI 测试
  - 覆盖 `status`、`teams info`、`install --dry-run`
- [ ] **路径解析统一审计**
  - 扫描所有 `Path(__file__)` 硬编码，统一使用 `_resolve_data_dir` / `_TEAMS_CONFIG_PATH.parent`
- [ ] **Release 前 smoke test**
  - `build-check` 后增加 "install wheel and run status" 步骤
- [ ] **版本预检脚本**
  - 打 tag 前自动检查 PyPI 是否已存在该版本

#### 8.2 TaskRouter - 任务路由智能

```python
# 目标: 自动任务分类和路由

class TaskRouter:
    def route(self, task: str) -> AgentChain:
        # 语义理解任务类型
        # 自动选择最佳 team 和 workflow pattern
        # 动态调整执行策略
```

**实现方案**:
- 使用轻量级规则 + LLM 分类的混合策略
- 在 `kimi_tachi/orchestrator.py` 中实现 `TaskRouter`
- 本地快速分类（无需 LLM）：基于关键词匹配 + 文件扩展名分析
- 复杂/模糊任务：用 `calcifer` 做一次性 LLM 分类（< 1s）

**工作流程**:
```
用户输入任务
     ↓
[TaskRouter] 分析任务类型
     ↓
选择 Team + Workflow 模板
     ↓
如果是复杂任务 → 触发 Plan Mode
     ↓
动态分配角色执行
     ↓
结果整合返回
```

#### 8.3 Plan Mode 集成

利用 kimi-cli 原生的 Plan Mode 优化编排流程：

```
当前流程:                        优化后流程:
                                
kimi-tachi 启动 kamaji          kimi-tachi 启动 kamaji
         │                              │
         ▼                              ▼
   kamaji 处理所有               [TaskRouter] 分析任务
         │                        /              \
         ▼                       /                \
   子 agent 协作              简单任务            复杂任务
                              (直接运行)         EnterPlanMode
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
- [ ] 在 `kamaji.yaml` system prompt 中加入 Plan Mode 触发逻辑
- [ ] 新增 `orchestrator/router.py` 实现 `TaskRouter`
- [ ] CLI 增加 `--plan` / `--no-plan` 选项覆盖自动判断
- [ ] 测试不同任务类型的路由准确率

#### 8.4 Background Bash 集成

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
- [ ] 在 `workflow_patterns` 中标记哪些步骤可后台化
- [ ] 测试长构建任务的异步执行

#### 8.5 Agent 提示词优化

应用 **自由度光谱** 优化现有 agent prompts：

| Agent | 自由度 | 优化方向 |
|-------|--------|----------|
| **tasogare** | 高 | 增加创造性指令，减少约束 |
| **shishigami** | 中 | 提供架构模式选项，允许变通 |
| **calcifer** | 低 | 提供代码生成脚本参考，锁定风格 |
| **enma** | 中 | 提供检查清单，标准化审查 |

**具体行动**:
- [ ] 为每个 Agent 编写反模式清单
- [ ] 优化 system prompt 为祈使语气
- [ ] 测试优化后的 Agent 表现

**里程碑**: v0.8.0 - 智能编排版

---

### v0.9.0: 记忆系统完善（后续，4-6 周）

**目标**: 完成真正的三层记忆系统，实现长期学习

#### 9.1 三层记忆系统

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

#### 9.2 MemNexus 后端真正落地

- [ ] 将 `hooks/tools.py` 中标记的 `# TODO: 实际存储到 memnexus` 完成
- [ ] 实现基于 MemNexus 的跨项目知识检索
- [ ] Agent 决策时自动检索相关历史经验

#### 9.3 用户偏好学习

- [ ] 学习用户偏好的代码风格
- [ ] 学习用户偏好的团队选择
- [ ] 自动调整 TaskRouter 权重

**里程碑**: v0.9.0 - 记忆智能版

---

### v1.0.0: 生态建设（未来）

**目标**: 构建 Skills 生态，支持自定义角色

#### 1.0.1 Skills 扩展

```
skills/
├── dev/                          # 开发相关
│   ├── code-generator/           # 代码生成
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

#### 1.0.2 自定义角色系统

```yaml
# 示例: 用户自定义角色模板
custom_agent_template:
  name: "my-agent"
  base_role: "calcifer"        # 继承火魔的基础能力
  
  customization:
    system_prompt_additions: |
      你专注于前端开发，擅长 React 和 TypeScript。
      你重视组件的可复用性和可访问性。
    
    skills:                      # 关联的 skills
      - "dev/code-generator"
      - "review/style-check"
    
    tools_priority:              # 工具使用偏好
      high: ["Glob", "Grep", "StrReplaceFile"]
      low: ["Shell"]
    
    freedom_level: "medium"      # high/medium/low
```

#### 1.0.3 社区与分享

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
| **v0.7.x** | wheel install 成功率 | 100% | 🔄 进行中 |
| **v0.7.x** | CI release 成功率 | 100% | 🔄 进行中 |
| **v0.8.0** | 任务路由准确率 | ≥ 85% | 📋 待开始 |
| **v0.8.0** | Plan Mode 触发正确率 | ≥ 90% | 📋 待开始 |
| **v0.9.0** | Working Memory 命中率 | ≥ 90% | 🔄 进行中 |
| **v1.0.0** | Skills 数量 | ≥ 10 | 📋 待开始 |
| **v1.0.0** | 社区贡献角色 | ≥ 5 | 📋 待开始 |

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
