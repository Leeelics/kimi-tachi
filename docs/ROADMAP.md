# kimi-tachi Roadmap

> **定位**：kimi-tachi 是 kimi-cli 原生能力的 team-based 放大器。
> 
> **核心原则**：不造新轮子，把 kimi-cli 已有的 subagent、hooks、skills、plugins、background tasks、todo、plan mode、DMail 等原子能力，通过主题化 team 编排成用户一句话就能调用的完整工作流。
>
> 最后更新: 2026-04-10

---

## 一、现状与核心问题

### 1.1 已有的底子
- **Plugin 体系**：kimi-tachi 以 kimi-cli 1.25.0+ plugin 形式分发，提供 workflow、memory、agent info 等工具
- **Multi-team 架构**：`agents/teams.yaml` 已支持多团队（coding / content），TeamManager 负责团队切换和隔离
- **编排器骨架**：`HybridOrchestrator`、`WorkflowEngine`、`ContextManager`、`SessionManager` 已就位
- **消息总线 + Tracing**：`MessageBus`、agent tracer、workflow visualization 已具备基础能力
- **Hooks 接入**：`hooks/` 下有 `recall-on-start.sh`、`store-before-compact.sh` 等生命周期脚本

### 1.2 致命短板：我们在「壳子上雕花」

kimi-tachi 目前最大的结构性问题是：**大量能力停留在「模拟」和「外部 shell 调用」，没有真正调用 kimi-cli 的原生工具。**

| kimi-cli 原生能力 | kimi-tachi 当前状态 | 问题 |
|---|---|---|
| `Agent` tool (subagent spawn + resume + background + timeout) | ❌ **未真正使用** | `workflow.py` 靠 `python3 scripts/workflow.py` shell 执行，而不是调用 `Agent()` |
| `Background` task (自动通知 + `TaskOutput` 轮询) | ❌ **模拟中** | `background/task_manager.py` 明确标注 "For now, we simulate the behavior" |
| `ExitPlanMode` (原生 Plan Mode 多选项提交) | ❌ **未接入** | tasogare 输出文本计划，没走 kimi-cli 的原生计划提交流程 |
| `SetTodoList` + `TodoDisplayBlock` | ⚠️ **只检查了格式** | `todo-enforcer` 是外部校验器，没有在 workflow 中主动调用原生 Todo 工具 |
| `SendDMail` (checkpointed 跨 agent 通信) | ❌ **完全没碰** | 自研 `MessageBus` 做异步通信，但 kimi-cli 已有 DMail |
| `SubagentStore` (session 级 subagent 持久化与恢复) | ❌ **未利用** | 自己存 `~/.kimi-tachi/memory/hooks/session_*.json`，而 kimi-cli 已自动存 `session/subagents/<agent_id>/` |
| Wire hooks (client-side real-time 注入) | ⚠️ **只到 shell 级别** | 当前 hooks 是 shell 脚本，没做 deeper wire subscription |

**结论**：kimi-tachi 在 kimi-cli 外面盖了一座自己的城堡，但这座城堡的很多砖块 kimi-cli 已经免费提供，而且做得更稳。

---

## 二、从竞品学到的关键洞察

### 2.1 superpowers — 自动化触发的工作流
- **核心启示**：skill 不是被用户手动调用的，而是**被意图自动触发**的
- ** kimi-tachi 应用**：用 kimi-cli 的 `UserPromptSubmit` hook 做意图识别，自动推荐/激活 flow skills；用 `ExitPlanMode` 在关键节点让用户做结构化选择

### 2.2 oh-my-opencode — 分类路由 + 并行 background agent
- **核心启示**：`IntentGate` + 按任务类别路由 + `Agent(run_in_background=True)` 并行执行
- **kimi-tachi 应用**：在 `category-router` 基础上，真正调用 `Agent(..., run_in_background=True)` 并行 spawn 多个子代理，用 `TaskOutput` 轮询结果

### 2.3 everything-claude-code — AGENTS.md 自动生成 + 持续学习
- **核心启示**：`/init-deep` 和 continuous learning 是最深的壁垒
- **kimi-tachi 应用**：用 `Agent` tool spawn nekobasu 扫描项目结构，生成层级 `AGENTS.md`；用 `SessionEnd` / `PostCompact` hooks 自动提取决策并存入 memory/skills

---

## 三、重构后的战略方向

### 3.1 反定位（绝对不做）
- ❌ 不造自己的 edit protocol（没有 Hashline）
- ❌ 不做跨平台兼容（不追 Cursor / Codex / OpenCode）
- ❌ 不堆 47 个 agent / 181 个 skill
- ❌ 不做 Web UI / 复杂配置面板
- ❌ 不直接暴露子代理给用户（ Coordinator-as-Face 不变）

### 3.2 核心行动纲领
> **把所有「shell 调用」和「模拟实现」替换成 kimi-cli 的原生工具调用。**

kimi-tachi 不应该有自己的并行执行系统、自己的 subagent 持久化系统、自己的后台任务系统。它应该是：**基于 kimi-cli 原生能力之上的一层智能编排胶水。**

---

## 四、迭代路线图

### Phase 0: 止血与根基（立即，1 周内）

**目标**：修复已损坏的 plugin 工具，补齐测试，让现有功能不再「丢人」。

- [ ] **修复缺失的 plugin 脚本**
  - `plugins/kimi-tachi/scripts/session_status.py` 缺失
  - `plugins/kimi-tachi/scripts/list_tasks.py` 缺失
  - 这些脚本不应该只是查本地状态，而应**直接对接 kimi-cli 的 background task API**

- [ ] **补齐 E2E 测试**
  - CI 中增加 wheel build → `pip install` → 运行 `kimi-tachi status/teams info` 的 smoke test
  - 确保 release 前能提前发现路径解析、依赖缺失等问题

- [ ] **统一路径解析**
  - 扫描所有 `Path(__file__)` 硬编码，统一使用 `_resolve_data_dir()`
  - 修复 wheel install 后的路径漂移问题

- [ ] **更新文档漂移**
  - `AGENTS.md` 中引用的 `team.py`、`orchestrator.py` 等单文件已拆包，需同步更新为 `team/`、`orchestrator/` 目录结构

---

### Phase 1: 从 Shell 到 Native（2-4 周）

**目标**：把 kimi-tachi 的核心执行路径从「shell 脚本」迁移到「kimi-cli 原生工具调用」。

#### 1.1 Workflow: 用 `Agent` tool 替换 `python3 scripts/workflow.py`

**当前问题**：
```json
// plugin.json
{
  "name": "workflow",
  "command": ["python3", "scripts/workflow.py"]
}
```
这启动了一个外部 Python 进程，完全在 kimi-cli 的 runtime 之外运行。

**目标状态**：
- Kamaji 收到任务后，直接调用 kimi-cli 原生的 `Agent` tool
- 根据 workflow type 决定 `subagent_type`：`explore` → nekobasu, `plan` → tasogare, `coder` → calcifer
- 复杂任务通过多步 `Agent()` 调用编排，而不是外部进程

**具体改动**：
- [ ] 重写 `orchestrator/native_agent_orchestrator.py`，使其**实际产出 `Agent` tool 调用参数**
- [ ] 废弃或降级 `scripts/workflow.py`，改为由 Kamaji 直接调用 `Agent()`
- [ ] 在 `kamaji.yaml` system prompt 中明确教导："当需要执行 workflow 时，使用 `Agent` tool，而不是 shell"

#### 1.2 Background Tasks: 从模拟到真用

**当前问题**：
```python
# background/task_manager.py
"In a real implementation, this would use the Agent tool with
run_in_background=True. For now, we simulate the behavior."
```

**目标状态**：
- `BackgroundTaskManager.start_task()` 直接封装 `Agent(..., run_in_background=True)`
- 用 `TaskOutput` 做状态轮询，用 kimi-cli 的自动通知机制替代手工模拟
- `list_tasks.py` 调用 kimi-cli 原生的 task listing API

**具体改动**：
- [ ] 重构 `background/task_manager.py`，删除模拟逻辑
- [ ] 对接 `Agent` tool 的 `run_in_background` + `timeout` 参数
- [ ] 修复 `list_tasks.py` 和 `session_status.py`，使其能正确查询 background task 状态

#### 1.3 Todo 工具：从「外部检查器」到「主动管理者」

**当前问题**：`todo-enforcer` 只是在 task 完成后检查格式，没有在 workflow 中主动使用 `SetTodoList`。

**目标状态**：
- workflow 开始时，Kamaji 自动 `SetTodoList` 创建任务
- 每个 subagent 完成阶段后，自动更新对应 todo 状态
- 利用 kimi-cli 原生的 `TodoDisplayBlock` 给用户可视化的进度条

**具体改动**：
- [ ] 在 `kamaji.yaml` 中加入 "workflow 启动时必须调用 `SetTodoList`"
- [ ] 在 `workflow_patterns` 的每个阶段节点定义对应的 todo item
- [ ] 在 `native_agent_orchestrator.py` 中增加 "post-agent todo update" 逻辑

#### 1.4 Plan Mode: 接入 `ExitPlanMode`

**当前问题**：tasogare 输出文本计划，用户需要在聊天记录里回复选择。

**目标状态**：
- tasogare / shishigami 做完规划后，调用 `ExitPlanMode` 提交 2-3 个选项
- 用户在 UI 中做结构化选择（Approve / Revise / Reject）
- 选择结果自动路由到下一个执行 agent

**具体改动**：
- [ ] 在 `tasogare.yaml` 和 `shishigami.yaml` 中加入 `ExitPlanMode` 的使用指引
- [ ] 在 `orchestrator/workflow_engine.py` 中增加 "plan mode checkpoint" 节点类型
- [ ] 测试 feature / refactor 类型任务的 Plan Mode 触发

---

### Phase 2: 记忆与状态 Native 化（4-6 周）

**目标**：停止自己造持久化轮子，全面利用 kimi-cli 的 `SubagentStore`、`DMail`、Hooks 和 Context Compaction。

#### 2.1 利用 `SubagentStore` 做跨会话恢复

**当前问题**：自己存 `~/.kimi-tachi/memory/hooks/session_*.json`。

**目标状态**：
- kimi-cli 已经自动将 subagent 实例元数据、prompts、wire logs 存到 `session/subagents/<agent_id>/`
- kimi-tachi 利用这个目录实现 "Resume previous team session"
- 用户下次进入同项目会话时，可以 `Agent(resume="...")` 继续之前的子代理

**具体改动**：
- [ ] 研究 `SubagentStore` 的存储格式和恢复机制
- [ ] 在 `session_manager.py` 中增加 "resume last team session" 功能
- [ ] 在 `hooks/recall-on-start.sh` 中读取 `SubagentStore` 的残留状态而非自定义 JSON

#### 2.2 DMail: 替换部分 MessageBus 功能

**当前问题**：`MessageBus` 是自研的异步消息总线，但在 kimi-cli runtime 内，很多 checkpoint 通信可以用 `SendDMail` 完成。

**目标状态**：
- 需要「持久化消息」的场景（如 compaction 前保存关键上下文）使用 `SendDMail`
- `MessageBus` 保留用于实时广播、tracing、vis 等纯观测类场景
- 减少自研通信系统的维护负担

**具体改动**：
- [ ] 在 `context/manager.py` 中增加 `DMailCheckpoint` 封装
- [ ] 将 `hooks/store-before-compact.sh` 的核心逻辑改为发送 DMail
- [ ] 评估 `MessageBus` 中哪些 pub/sub 可以迁移到 DMail

#### 2.3 Hooks: 从 Shell 升级到 Wire Subscription

**当前问题**：所有 hooks 都是 shell 脚本，能力有限（只能执行外部命令）。

**目标状态**：
- 把关键的 `PreToolUse`、`PostToolUse`、`UserPromptSubmit`、`PreCompact` hooks 升级为 kimi-cli 的 client-side wire subscriptions
- 实现更实时的 context injection、tool guard、todo enforcement

**具体改动**：
- [ ] 研究 `src/kimi_cli/hooks/engine.py` 的 wire hook 注册机制
- [ ] 在 `src/kimi_tachi/hooks/` 中增加 Python 版的 wire hook handler
- [ ] 逐步将 `recall-on-start.sh`、`trace-agent.sh`、`store-before-compact.sh` 的逻辑 Python 化

#### 2.4 自动记忆：利用 compaction hooks 做零配置知识沉淀

**目标状态**：
- `PreCompact`：用 DMail / 自定义逻辑保存当前会话的关键决策
- `PostCompact`：自动将提取的决策存入 `memory_store_decision`
- `SessionEnd`：自动总结本次会话，存入 episodic memory
- 用户完全无感知

**具体改动**：
- [ ] 打通 `hooks/tools.py` 中标记的 `# TODO: 实际存储到 memnexus`
- [ ] 完成 `tachi_memory_v3.py` 的 MemNexus 后端对接
- [ ] 实现自动决策提取 + 去重 + 存储的完整 pipeline

---

### Phase 3: 智能编排与生态（6-10 周）

**目标**：在原生能力扎实的基础上，做 kimi-tachi 的差异化护城河。

#### 3.1 TaskRouter: 意图识别 + 自动 team/workflow 选择

**目标状态**：
- 用户输入任务后，系统自动判断该用哪个 team、哪种 workflow pattern
- 简单任务直接走 fast path（关键词匹配 + 文件扩展名分析）
- 复杂/模糊任务用一次性的轻量 LLM 调用做分类

**具体改动**：
- [ ] 实现 `orchestrator/router.py`
- [ ] 定义任务分类规则（feature / bugfix / explore / refactor / content / etc.）
- [ ] 在 `kamaji.yaml` 中加入 TaskRouter 的使用指引
- [ ] 测试不同任务类型的路由准确率 ≥ 85%

#### 3.2 `/init-deep` 等价能力：自动 AGENTS.md 生成

**目标状态**：
- 用户在新项目使用 kimi-tachi 时，可以自动扫描项目结构
- nekobasu 做快速探查 → calcifer 生成层级 `AGENTS.md`
- 生成的文档自动存入项目根目录和关键子目录

**具体改动**：
- [ ] 在 skills 中新增 `project-onboarding` skill
- [ ] 实现 "scan → generate → write AGENTS.md" 的 workflow
- [ ] 与 MemNexus 集成：将项目结构知识存入 semantic memory

#### 3.3 Team 扩展：新增主题团队

**目标状态**：
- 在现有 `coding`（七人衆）和 `content`（三国天团）基础上，新增实用 team
- 候选：
  - `review` team：专门做 security review、performance review、style review
  - `devops` team：CI/CD、部署、监控配置
  - `data` team：数据科学、ML pipeline

**具体改动**：
- [ ] 设计新 team 的 YAML 结构（coordinator + agents + workflow_patterns）
- [ ] 建立 "add new team" 的标准模板和测试清单
- [ ] 让 `TeamManager` 支持动态加载用户自定义 team

#### 3.4 Skills 生态：从示例到实用

**目标状态**：
- 把现有的 `category-router`、`todo-enforcer`、`kimi-tachi` skills 做深
- 新增 3-5 个与 workflow 紧密集成的实用 skills
- 建立 skill 开发模板和贡献指南

**候选 skills**：
- `project-onboarding`：新项目初始化 + AGENTS.md 生成
- `build-troubleshooter`：构建失败自动诊断和修复
- `refactor-planner`：大规模重构的拆分和风险评估
- `test-strategist`：测试策略设计和覆盖率分析

---

## 五、成功指标

| 维度 | 指标 | Phase 0 目标 | Phase 1 目标 | Phase 2 目标 | Phase 3 目标 |
|---|---|---|---|---|---|
| **稳定性** | wheel install smoke test 通过率 | 100% | 100% | 100% | 100% |
| **原生集成** | shell-based workflow 占比 | 100% | 0% | 0% | 0% |
| **原生集成** | 模拟 background task 占比 | 100% | 0% | 0% | 0% |
| **原生集成** | Plan Mode 使用率（复杂任务） | 0% | ≥ 50% | ≥ 80% | ≥ 90% |
| **原生集成** | Todo 工具主动使用率 | 0% | ≥ 50% | ≥ 80% | ≥ 90% |
| **记忆** | 跨会话恢复成功率 | N/A | N/A | ≥ 70% | ≥ 85% |
| **编排** | TaskRouter 准确率 | N/A | N/A | N/A | ≥ 85% |
| **生态** | 实用 skills 数量 | 3 | 4 | 5 | ≥ 8 |
| **生态** | 支持 team 数量 | 2 | 2 | 3 | ≥ 4 |

---

## 六、本周立即行动清单

1. [ ] 创建 `plugins/kimi-tachi/scripts/session_status.py`
2. [ ] 创建 `plugins/kimi-tachi/scripts/list_tasks.py`
3. [ ] 在 CI 中增加 wheel install E2E smoke test
4. [ ] 起草 `orchestrator/router.py` 的 TaskRouter 骨架（关键词 fast path）
5. [ ] 评估 `scripts/workflow.py` 中哪些逻辑可以迁移到 `Agent()` 原生调用

---

## 七、第一性原理总结

> **kimi-tachi 不是要成为最好的 AI 编码团队，而是要成为 kimi-cli 最好的「能力放大器」。**
>
> 我们不造自己的 edit protocol、不跨平台、不堆 agent 数量。
> 我们只做好一件事：**用户说目标，我们自动调用 kimi-cli 的原生能力（Agent、Background、Todo、Plan、DMail、Hooks、Memory）去完成它。**
>
> 用户感知到的不是 "我用了 subagent + hooks + skills + memory"，而是 "我的 team 把这事办了"。

---

## 相关文档

- [anti-patterns.md](./anti-patterns.md) - 反模式清单
- [memory.md](./memory.md) - 记忆系统文档
- [hooks.md](./hooks.md) - Hooks 集成指南
- [contributing.md](./contributing.md) - 贡献指南
- [../AGENTS.md](../AGENTS.md) - 项目架构与开发规范
