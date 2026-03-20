# kimi-tachi Roadmap

> 基于 kimi-cli 源码分析和 hello-agents 最佳实践的策略性迭代计划
> 
> 最后更新: 2026-03-20

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

### Phase 2: 架构优化（6-8 周）

**目标**: 重构 Agent 层级，引入消息驱动架构

#### 2.1 Agent 层级重新设计

```
当前设计（问题）:
  kamaji (fixed)
    ├── shishigami (fixed) ← 都加载 MCP
    ├── nekobasu (fixed)   ← 都加载 MCP
    ├── calcifer (fixed)   ← 都加载 MCP
    ├── enma (fixed)       ← 都加载 MCP
    ├── tasogare (fixed)   ← 都加载 MCP
    └── phoenix (fixed)    ← 都加载 MCP
    
结果: 7 个 Agent × N 个 MCP 服务器 = 资源爆炸

优化设计（推荐）:
  kamaji (fixed, 轻量)
    ├── 配置最小化，不包含 subagents 定义
    └── 通过 Task 工具调用其他角色
    
或:
  kamaji (fixed)
    └── 使用 CreateSubagent 动态创建临时角色
    
结果: 只有 kamaji 加载 MCP（如果需要）
```

#### 2.2 消息总线架构（新增）

参考 AgentScope 的消息驱动设计：

```python
# 消息总线设计
class MessageHub:
    """Agent 间消息中心"""
    
    async def send(self, from_agent: str, to_agent: str, message: Message):
        """点对点消息"""
        
    async def broadcast(self, from_agent: str, message: Message):
        """广播消息"""
        
    async def multicast(self, from_agent: str, to_agents: list[str], message: Message):
        """组播消息"""
```

**应用场景**:
```
协作场景:
┌─────────────────────────────────────────┐
│  kamaji (协调器)                         │
│     │                                   │
│     ├── 发送任务给 nekobasu              │
│     │     ↓                             │
│     ├── nekobasu 完成后广播结果          │
│     │     ↓                             │
│     ├── calcifer 和 enma 并行处理        │
│     │     ↓                             │
│     └── 收集结果，整合输出               │
└─────────────────────────────────────────┘
```

**具体行动**:
- [ ] 设计 MessageHub 接口
- [ ] 改造 Task 工具为消息驱动模式
- [ ] 实现消息持久化和重放

#### 2.3 Workflow 引擎完善

```python
# 目标: 完善的 workflow 类型支持

workflows = {
    "feature":     # 新功能实现
        "tasogare(plan) → nekobasu(explore) → shishigami(arch) → calcifer(impl) → enma(review)",
    
    "bugfix":      # Bug 修复
        "nekobasu(locate) → shishigami(analyze) → calcifer(fix) → enma(verify)",
    
    "explore":     # 代码探索
        "nekobasu(navigate) → phoenix(document)",
    
    "refactor":    # 安全重构
        "phoenix(history) → shishigami(design) → calcifer(refactor) → enma(verify)",
    
    "quick":       # 快速修复
        "calcifer(direct)"
}
```

#### 2.4 上下文传递优化

```
优化方向:
1. 利用 SessionState 持久化
   - approval 状态 (YOLO mode)
   - 动态创建的 subagent
   - workflow 执行状态

2. 减少 Task 间重复加载
   - 代码库索引缓存
   - 符号表缓存
   - 用户偏好记忆
```

**具体行动**:
- [ ] 重构 `agents/kamaji.yaml`，简化 subagents 定义
- [ ] 完善 `src/kimi_tachi/orchestrator/` workflow 引擎
- [ ] 实现代码库索引缓存机制
- [ ] 添加 workflow 执行状态持久化

**里程碑**: v0.3.0 - 架构优化版

---

### Phase 3: 记忆与智能（8-12 周）

**目标**: 实现跨角色记忆共享，参考 hello-agents 记忆分层设计

#### 3.1 记忆系统层级（基于 hello-agents Chapter 8）

```
┌─────────────────────────────────────────────────────────┐
│  记忆层级设计（参考 hello-agents）                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  Working Memory（工作记忆）             │
│  │  短期记忆   │  - 当前会话上下文                       │
│  │  (kimi-cli) │  - approval 状态                        │
│  │             │  - 动态 subagent 状态                   │
│  └──────┬──────┘                                        │
│         │                                               │
│  ┌──────▼──────┐  Episodic Memory（情景记忆）            │
│  │  中期记忆   │  - .kimi-tachi/memory/                  │
│  │  (kimi-     │    - sessions/history.json              │
│  │   tachi)    │    - sessions/summary.json              │
│  │             │    - sessions/decisions.json            │
│  └──────┬──────┘                                        │
│         │                                               │
│  ┌──────▼──────┐  Semantic Memory（语义记忆）            │
│  │  长期知识   │  - 代码库理解（符号、模式）              │
│  │  (phoenix)  │  - 技术栈文档索引                       │
│  │             │  - 跨项目最佳实践                       │
│  └──────┬──────┘                                        │
│         │                                               │
│  ┌──────▼──────┐  Procedural Memory（程序记忆）          │
│  │  技能记忆   │  - Skill 执行记录                       │
│  │  (skills)   │  - 常用操作序列                         │
│  │             │  - 用户习惯模式                         │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 Project 记忆存储结构

```
.kimi-tachi/
├── memory/
│   ├── working/               # Working Memory 快照
│   │   └── current_session.json
│   │
│   ├── episodic/              # Episodic Memory
│   │   ├── sessions/          # 会话历史
│   │   │   ├── 2026-03-20-001.json
│   │   │   └── summary.json   # 会话摘要索引
│   │   ├── decisions.json     # 关键决策记录
│   │   └── learnings.json     # 学习到的经验
│   │
│   ├── semantic/              # Semantic Memory
│   │   ├── codebase/          # 代码库理解
│   │   │   ├── symbols.json   # 符号索引（类、函数、变量）
│   │   │   ├── patterns.json  # 代码模式（架构、约定）
│   │   │   └── dependencies.json  # 依赖关系图
│   │   ├── docs/              # 文档索引
│   │   │   └── tech_stack.json
│   │   └── best_practices/    # 最佳实践库
│   │
│   └── procedural/            # Procedural Memory
│       ├── skill_history/     # Skill 执行记录
│       └── user_patterns.json # 用户操作模式
│
├── state/
│   └── workflow_state.json    # 当前 workflow 状态
│
└── cache/
    └── file_index.json        # 文件索引缓存
```

#### 3.3 记忆增强 Agent 设计

**phoenix（图书管理员）记忆增强**:

```yaml
# phoenix.yaml 增强
system_prompt_additions: |
  你是火之鸟，拥有永恒的记忆。你可以访问以下记忆：
  
  ## Working Memory（当前会话）
  - 当前任务上下文
  - 已执行的操作序列
  
  ## Episodic Memory（历史经验）
  - 类似任务的过往解决方案
  - 用户的历史偏好
  
  ## Semantic Memory（知识库）
  - 项目代码结构和模式
  - 技术栈文档
  
  当用户询问时，主动检索相关记忆提供上下文。
```

**智能任务路由**:

```
基于历史学习的 Agent 选择:

输入: 任务描述
   │
   ▼
┌─────────────┐
│  模式匹配   │ ← 查询 procedural/skill_history.json
│  (phoenix)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  历史相似度 │ ← 查询 episodic/summary.json
│  分析       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Agent 推荐 │
│  排序       │
└──────┬──────┘
       │
       ▼
   执行决策
```

**具体行动**:
- [ ] 实现 Working Memory 管理器
- [ ] 实现 Episodic Memory（会话存储与检索）
- [ ] 实现 Semantic Memory（代码库索引）
- [ ] 增强 phoenix 角色的记忆检索能力
- [ ] 开发智能任务路由算法

**里程碑**: v0.4.0 - 记忆增强版

---

### Phase 4: 生态建设（12 周+）

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

## 🎯 近期行动项（本周可开始）

### 优先级 0: Skill 架构升级

```bash
# 1. 设计新的 Skill 目录结构
mkdir -p skills/example/{scripts,references}

# 2. 编写反模式清单模板
# 参考 hello-agents Extra08
```

**Action Items**:
- [ ] 为现有 skills 添加 scripts/ 目录
- [ ] 为每个 Agent 编写反模式清单
- [ ] 优化 system prompt 为祈使语气

### 优先级 1: MCP 问题缓解

```bash
# 测试无 MCP 环境下的表现
kimi --agent-file agents/kamaji.yaml
```

**Action Items**:
- [ ] 修改 `agents/kamaji.yaml`，移除 subagents 中的 MCP 依赖
- [ ] 在 README 中添加 MCP 使用注意事项
- [ ] 验证无 MCP 时的核心功能稳定性

### 优先级 2: Plan Mode 实验

```bash
# 测试 kimi-cli v1.24 的 Plan Mode
kimi --agent-file agents/kamaji.yaml

# 输入复杂任务，测试自动进入 Plan Mode 的效果
# 例如: "实现一个用户认证系统"
```

**Action Items**:
- [ ] 更新 `kamaji.yaml` system prompt，加入 Plan Mode 触发逻辑
- [ ] 测试 3-5 个复杂任务的 Plan Mode 流程
- [ ] 收集反馈，优化触发条件和呈现方式

---

## 📋 与上游协作计划

| 问题 | 提议 | 优先级 | 状态 |
|------|------|--------|------|
| MCP 重复启动 | 向 kimi-cli 提交 Issue | High | 待提交 |
| Subagent 间工具共享 | 提议 `shared_toolset` 参数 | Medium | 待评估 |
| Agent 编排 API | 提议高层编排接口 | Low | 规划中 |
| Session 状态扩展 | 提议 workflow 状态持久化 | Low | 待评估 |
| **Skill 三级加载** | 提议标准 Skill 结构规范 | Medium | 待评估 |

---

## 📈 成功指标

| 阶段 | 指标 | 目标值 |
|------|------|--------|
| **Phase 0** | Skill 完成三级分层迁移 | 100% |
| **Phase 0** | Agent 提示词优化覆盖率 | 100% |
| **Phase 1** | MCP 进程数 | ≤ 2（如使用） |
| **Phase 1** | Plan Mode 触发准确率 | ≥ 80% |
| **Phase 2** | Workflow 完成率 | ≥ 90% |
| **Phase 2** | 上下文重复加载减少 | ≥ 50% |
| **Phase 2** | 消息总线延迟 | < 100ms |
| **Phase 3** | Working Memory 命中率 | ≥ 90% |
| **Phase 3** | Episodic Memory 检索准确率 | ≥ 80% |
| **Phase 3** | Semantic Memory 代码库覆盖率 | ≥ 70% |
| **Phase 3** | 任务路由准确率 | ≥ 85% |
| **Phase 4** | Skills 数量 | ≥ 10 |
| **Phase 4** | 社区贡献角色 | ≥ 5 |

---

## 🔗 相关文档

- [VISION.md](./VISION.md) - 设计理念与角色设定
- [STATUS.md](./STATUS.md) - 当前状态与进度
- [AGENTS.md](./AGENTS.md) - 开发指南与规范
- [BUG_REPORT_MCP_DUPLICATION.md](./BUG_REPORT_MCP_DUPLICATION.md) - MCP 问题详细分析
- [GITHUB_SETUP.md](./GITHUB_SETUP.md) - CI/CD 配置指南
- [hello-agents](https://github.com/datawhalechina/hello-agents) - 智能体系统最佳实践参考
- [kimi-cli CHANGELOG](https://github.com/your-org/kimi-cli/blob/main/CHANGELOG.md) - 上游更新日志

---

*「七人の力が一つになれば、どんな敵にも負けない。」*
*（七人的力量合为一体，任何敌人都无法战胜。）*
