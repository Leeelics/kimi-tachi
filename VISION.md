# kimi-tachi 愿景与路线图

## 为什么创建 kimi-tachi？

### 背景

Kimi CLI 是一个优秀的 AI 编程助手，但在复杂工程任务中，单一代理往往难以兼顾所有方面：
- 架构设计需要深度思考
- 代码实现需要细致执行
- 代码审查需要批判性思维
- 知识检索需要广度搜索

### 问题

**Kimi CLI 的限制：**
1. 没有原生多代理编排机制
2. 缺乏工程化可靠性保障（如强制 Todo 检查）
3. 复杂任务的上下文管理依赖用户手动控制

**其他方案的不足：**
- OpenCode: 需要切换工具生态
- Claude Code: 闭源，无法自定义
- Aider: 主要针对结对编程

### 愿景

> **让 Kimi CLI 成为最懂工程化实践的 AI 编程助手**

kimi-tachi 不是要替代 Kimi CLI，而是作为**编排层**，让多个专业代理协同工作，实现：

1. **专业化分工** - 每个代理专注于自己擅长的领域
2. **可靠性保障** - 强制流程检查，确保任务完成质量
3. **零侵入集成** - 不修改 Kimi CLI 源码，纯配置扩展

---

## 核心设计哲学

### 1. 原生优先 (Native First)

```
能用 Kimi CLI 原生的，绝不多造轮子
```

| 功能 | 我们的选择 | 理由 |
|------|-----------|------|
| 子代理 | Task 工具 | 原生支持，上下文隔离 |
| 文件编辑 | StrReplaceFile | 足够强大，无需 hashline |
| 配置 | config.toml | 单一配置源，用户友好 |
| 进程通信 | Wire 协议 | 官方协议，稳定可靠 |

### 2. 渐进增强 (Progressive Enhancement)

```
基础功能开箱即用，高级功能按需启用
```

- **Phase 1**: 基础多代理（今天就能用）
- **Phase 2**: Skills 增强（提升可靠性）
- **Phase 3**: 记忆系统（长期知识）
- **Phase 4**: 自定义工具（高级用户）

### 3. 工程化可靠性 (Engineering Reliability)

从 oh-my-opencode 吸取的核心思想：

```
不是让 AI 写更多代码，而是让 AI 写对的代码
```

**具体措施：**
- ✅ Todo Enforcer - 强制任务追踪
- ✅ Category Router - 智能代理选择
- ✅ Momus Review - 强制代码审查
- 🚧 Checkpoint System - 状态保存与回滚
- 🚧 Ralph Loop - 自动迭代优化

---

## 与 oh-my-opencode 的关系

### 区别

| 维度 | oh-my-opencode | kimi-tachi |
|------|---------------|------------|
| **基础平台** | OpenCode | Kimi CLI |
| **架构** | Hooks + Plugin | Native Agent + Skill |
| **侵入性** | 深度集成 | 零侵入 |
| **多代理** | 并行 Background Agent | 顺序 Task 委派 |
| **适用场景** | 大型工程 | 中小项目 |

### 共同点

1. **多代理专业化** - 代理分工协作
2. **Todo 强制执行** - 可靠性保障
3. **分层记忆** - 知识管理
4. **工程化流程** - 规范化实践

### 设计理念继承

从 oh-my-opencode 学习：
- "Do not write more code, write correct code"
- "Trust but verify"
- "Explicit is better than implicit"

---

## 长期愿景

### 短期（3 个月）

- [ ] 7 个核心 Agent 稳定可用
- [ ] 5+ 实用 Skills
- [ ] 基础记忆系统
- [ ] 社区贡献指南

### 中期（6 个月）

- [ ] Agent 市场（社区共享 Agent 配置）
- [ ] Skill 市场（社区共享 Skills）
- [ ] 可视化调试工具
- [ ] 性能分析与优化

### 长期（12 个月）

- [ ] 与 Kimi CLI 官方深度合作
- [ ] 企业级功能（团队协作、权限管理）
- [ ] 多模态支持（图像、音频）
- [ ] 自动测试与验证

---

## 技术愿景

### 理想状态

```python
# 用户只需简单配置
[kimi_tachi]
team = ["sisyphus", "oracle", "hephaestus"]
workflow = "code-review-required"
memory = "enabled"

# 然后专注于描述需求
$ kimi-tachi do "实现一个高性能的缓存系统"

# kimi-tachi 自动：
# 1. sisyphus 拆解任务
# 2. oracle 设计架构
# 3. hephaestus 实现代码
# 4. momus 审查代码
# 5. 保存知识到 librarian
```

### 关键技术方向

1. **智能路由** - 基于任务内容自动选择最佳代理
2. **上下文压缩** - 长会话的智能摘要与恢复
3. **知识沉淀** - 代码模式、决策记录、最佳实践
4. **人机协作** - 明确的分工边界，高效的人机交互

---

## 社区愿景

### 目标用户

1. **个人开发者** - 提升编码效率
2. **小团队** - 规范化工程实践
3. **开源项目** - 降低贡献门槛

### 贡献方式

- **Agent 作者** - 分享特定领域的专业代理
- **Skill 作者** - 分享工程化最佳实践
- **工具开发者** - 扩展 Kimi CLI 能力
- **文档贡献者** - 完善使用案例

### 生态设想

```
kimi-tachi/
├── core/              # 核心（官方维护）
│   ├── sisyphus/
│   ├── oracle/
│   └── todo-enforcer/
│
├── community/         # 社区贡献
│   ├── agents/
│   │   ├── frontend-expert/    # @community
│   │   ├── devops-master/      # @community
│   │   └── security-auditor/   # @community
│   │
│   └── skills/
│       ├── agile-workflow/     # @community
│       ├── tdd-guide/          # @community
│       └── doc-driven/         # @community
│
└── enterprise/        # 企业版（未来）
    ├── team-sync/
    ├── access-control/
    └── audit-log/
```

---

## 与 Kimi CLI 官方的关系

### 当前状态

- **独立项目** - 社区驱动
- **零侵入** - 不修改 Kimi CLI 源码
- **友好协作** - 使用官方扩展点

### 期望的未来

**理想情况：** kimi-tachi 的概念被 Kimi CLI 官方吸收

```
# 未来的 Kimi CLI 可能原生支持
$ kimi --team sisyphus
$ kimi --workflow todo-enforced
```

**现实路径：**
1. 证明多代理编排的价值
2. 积累社区使用案例
3. 与官方团队交流协作
4. 逐步标准化

---

## 成功指标

### 技术指标

- [ ] 7 个核心 Agent 稳定运行
- [ ] 平均任务完成率 > 90%
- [ ] 代码审查问题发现率 > 人工审查
- [ ] 复杂任务分解准确率 > 80%

### 社区指标

- [ ] 100+ GitHub Stars
- [ ] 10+ 社区贡献 Agent
- [ ] 5+ 企业用户案例
- [ ] 被 Kimi 官方博客/文档提及

### 个人指标

- [ ] 每天使用 kimi-tachi 完成真实工作
- [ ] 减少重复性编码工作 50%+
- [ ] 代码质量评分提升
- [ ] 学习和分享的过程

---

## 结语

> **kimi-tachi** - *Many Kimis, One Goal.*

我们不是在创造一个新的 AI 工具，而是在探索**人机协作编程**的最佳实践。

让 AI 代理像优秀的团队成员一样：
- 各司其职
- 互相配合
- 可靠交付
- 持续学习

这就是 kimi-tachi 的愿景。

---

**Start small, think big, move fast.**

从 Phase 1 的 5 个 Agent 开始，逐步构建这个愿景。每一步都应该是可用的、有价值的。
