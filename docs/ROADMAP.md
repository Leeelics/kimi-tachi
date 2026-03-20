# kimi-tachi Roadmap

> 基于 kimi-cli 源码分析的策略性迭代计划
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

---

## 🗺️ 迭代路线图

### Phase 1: 适配与稳定（4-6 周）

**目标**: 解决 MCP 问题，适配 kimi-cli 最新能力

#### Week 1-2: MCP 问题 Workaround

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

#### Week 3-4: Plan Mode 集成

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

#### Week 5-6: Background Bash 集成

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

**目标**: 重构 Agent 层级，优化上下文传递

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

#### 2.2 Workflow 引擎完善

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

#### 2.3 上下文传递优化

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

**目标**: 实现跨角色记忆共享，提升智能化水平

#### 3.1 记忆系统层级

```
┌─────────────────────────────────────────────────────────┐
│  记忆层级设计                                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  Session 级（kimi-cli 原生）           │
│  │  短期记忆   │  - approval 状态                        │
│  │  (自动)     │  - 动态 subagent 状态                   │
│  │             │  - 当前会话上下文                       │
│  └──────┬──────┘                                        │
│         │                                               │
│  ┌──────▼──────┐  Project 级（kimi-tachi 实现）         │
│  │  中期记忆   │  - .kimi-tachi/memory/                  │
│  │  (持久化)   │    - codebase/symbols.json              │
│  │             │    - codebase/patterns.json             │
│  │             │    - sessions/history.json              │
│  │             │    - learnings/user_prefs.json          │
│  │             │    - learnings/project_rules.json       │
│  └──────┬──────┘                                        │
│         │                                               │
│  ┌──────▼──────┐  Knowledge 级（phoenix 角色）          │
│  │  长期知识   │  - 跨项目最佳实践                       │
│  │  (知识库)   │  - 技术栈文档索引                       │
│  │             │  - 常见模式库                           │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 Project 记忆存储结构

```
.kimi-tachi/
├── memory/
│   ├── codebase/              # 代码库理解缓存
│   │   ├── symbols.json       # 符号索引（类、函数、变量）
│   │   ├── patterns.json      # 代码模式（架构、约定）
│   │   └── dependencies.json  # 依赖关系图
│   ├── sessions/              # 会话历史
│   │   ├── summary.json       # 会话摘要
│   │   └── decisions.json     # 关键决策记录
│   └── learnings/             # 学习到的知识
│       ├── user_prefs.json    # 用户偏好
│       ├── project_rules.json # 项目特定规则
│       └── common_fixes.json  # 常见修复模式
├── state/
│   └── workflow_state.json    # 当前 workflow 状态
└── cache/
    └── file_index.json        # 文件索引缓存
```

#### 3.3 智能路由

```
基于历史学习的 Agent 选择:

输入: 任务描述
   │
   ▼
┌─────────────┐
│  模式匹配   │ ← 查询 project_rules.json
│  (phoenix)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  历史相似度 │ ← 查询 sessions/summary.json
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
- [ ] 实现代码库符号索引（nekobasu 增强）
- [ ] 实现项目记忆存储机制
- [ ] 增强 phoenix 角色的知识检索能力
- [ ] 开发智能任务路由算法

**里程碑**: v0.4.0 - 记忆增强版

---

### Phase 4: 生态建设（12 周+）

**目标**: 构建 Skills 生态，支持自定义角色

#### 4.1 Skills 扩展

```
skills/
├── dev/                          # 开发相关
│   ├── code-generator/           # 代码生成
│   │   └── SKILL.md
│   ├── test-writer/              # 测试编写
│   │   └── SKILL.md
│   ├── doc-generator/            # 文档生成
│   │   └── SKILL.md
│   └── api-client/               # API 客户端生成
│       └── SKILL.md
├── review/                       # 代码审查
│   ├── security-check/           # 安全检查
│   │   └── SKILL.md
│   ├── performance/              # 性能分析
│   │   └── SKILL.md
│   └── style-check/              # 代码风格
│       └── SKILL.md
├── project/                      # 项目管理
│   ├── onboarding/               # 新成员引导
│   │   └── SKILL.md
│   ├── release/                  # 发布助手
│   │   └── SKILL.md
│   └── changelog/                # 变更日志
│       └── SKILL.md
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
    
    skills:                      # 关联的 skills
      - "dev/code-generator"
      - "review/style-check"
    
    tools_priority:              # 工具使用偏好
      high: ["Glob", "Grep", "StrReplaceFile"]
      low: ["Shell"]
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

### 优先级 1: MCP 问题缓解

```bash
# 1. 测试无 MCP 环境下的表现
kimi --agent-file agents/kamaji.yaml

# 2. 量化 MCP 重复启动的影响
# 在启用 MCP 时观察进程数量
ps aux | grep -E "playwright|context7" | wc -l
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

### 优先级 3: Agent 配置优化

```yaml
# 目标: 简化 fixed subagents，避免 MCP 重复加载
# 方式: 在 system_prompt 中指导 kamaji 如何使用 Task 工具

# kamaji.yaml 变更:
# - 可选: 完全移除 subagents 定义
# - 或: 保留定义但确保每个 subagent YAML 最小化
```

---

## 📋 与上游协作计划

| 问题 | 提议 | 优先级 | 状态 |
|------|------|--------|------|
| MCP 重复启动 | 向 kimi-cli 提交 Issue | High | 待提交 |
| Subagent 间工具共享 | 提议 `shared_toolset` 参数 | Medium | 待评估 |
| Agent 编排 API | 提议高层编排接口 | Low | 规划中 |
| Session 状态扩展 | 提议 workflow 状态持久化 | Low | 待评估 |

---

## 📈 成功指标

| 阶段 | 指标 | 目标值 |
|------|------|--------|
| Phase 1 | MCP 进程数 | ≤ 2（如使用） |
| Phase 1 | Plan Mode 触发准确率 | ≥ 80% |
| Phase 2 | Workflow 完成率 | ≥ 90% |
| Phase 2 | 上下文重复加载减少 | ≥ 50% |
| Phase 3 | 记忆命中率 | ≥ 70% |
| Phase 3 | 任务路由准确率 | ≥ 85% |
| Phase 4 | Skills 数量 | ≥ 10 |
| Phase 4 | 社区贡献角色 | ≥ 5 |

---

## 🔗 相关文档

- [VISION.md](./VISION.md) - 设计理念与角色设定
- [STATUS.md](./STATUS.md) - 当前状态与进度
- [BUG_REPORT_MCP_DUPLICATION.md](./BUG_REPORT_MCP_DUPLICATION.md) - MCP 问题详细分析
- [kimi-cli CHANGELOG](https://github.com/your-org/kimi-cli/blob/main/CHANGELOG.md) - 上游更新日志

---

*「七人の力が一つになれば、どんな敵にも負けない。」*
*（七人的力量合为一体，任何敌人都无法战胜。）*
