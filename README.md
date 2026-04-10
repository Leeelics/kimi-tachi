# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI

[![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## 是什么

**kimi-tachi** 是 Kimi CLI 的「外脑」——它不替代 kimi-cli 的执行引擎，而是为根 Agent（Kamaji）提供三样核心能力：

1. **团队配置** — 多主题 Agent 团队的安装与切换
2. **计划生成** — 根据任务类型生成对齐 kimi-cli 原生 `Agent()` 参数的结构化 workflow
3. **跨项目记忆** — 基于 MemNexus 的代码记忆（决策存档、Agent 上下文召回、全局模式搜索）

**执行权 100% 交给 kimi-cli 原生 runtime。** kimi-tachi 本身不调度 Agent、不管理 background task、不维护独立的 session store。

### 内置团队

| 团队 | 主题 | Coordinator | 适用场景 |
|------|------|-------------|----------|
| **coding** | 七人衆（宫崎骏/吉卜力）| 釜爺 (kamaji) | 编程开发、架构设计、代码审查 |
| **content** | 三国·自媒体天团 | 荀彧 (xunyu) | 内容创作、选题写作、排版设计 |

### coding 团队角色示例

| Agent | 角色 | 职责 | Emoji |
|-------|------|------|-------|
| **kamaji** | 釜爺 | 总协调 | ◕‿◕ |
| **nekobasu** | 猫バス | 代码探索 | 🚌 |
| **shishigami** | シシ神 | 架构设计 | 🦌 |
| **calcifer** | カルシファー | 代码实现 | 🔥 |
| **enma** | 閻魔大王 | 代码审查 | 👹 |
| **tasogare** | 黄昏時 | 任务规划 | 🌆 |
| **phoenix** | 火の鳥 | 知识管理 | 🐦 |

## 怎么用

### 安装与升级

```bash
# 首次安装
pip install kimi-tachi
kimi-tachi install

# 升级到新版本后，重新 install 即可更新 agents/skills/plugins
kimi-tachi install
```

要求：kimi-cli >= 1.25.0（测试至 1.30.0），Python >= 3.12

### 启动

```bash
# 直接启动（默认使用 kamaji）
kimi-tachi
```

### 团队切换

```bash
# 查看可用团队
kimi-tachi teams list

# 切换团队
kimi-tachi teams switch <team-id>
```

### 查看状态

```bash
kimi-tachi status
```

## 有什么效果

### 自动任务编排

kamaji 会根据任务复杂度自动调度合适的角色：

- **简单任务** → kamaji 直接处理
- **中等任务** → 🚌 探索后执行
- **复杂任务** → 🌆 规划 → 🚌 探索 → 🦌 架构 → 🔥 实现 → 👹 审查

### Native Tool Orchestration（v0.8.0+）

kimi-tachi 的 `workflow` plugin 只生成计划，**真正的编排发生在 Kamaji 的 system prompt 中**：

- 调用 `Agent(subagent_type=..., model=..., timeout=..., run_in_background=..., resume=...)` 执行每个 phase
- 调用 `SetTodoList()` 跟踪多阶段进度
- 调用 `TaskList()` / `TaskOutput()` 监控后台任务
- 调用 `ExitPlanMode()` 在规划阶段后提交计划选项给用户审批

`workflow.py` 输出的计划已 100% 对齐 kimi-cli 原生参数：
- `subagent_type` — `coder` / `explore` / `plan`
- `model` — 如 `shishigami` → `kimi-k2.5`
- `resume` — 连续同 agent 时复用上下文
- `plan_mode_reason` — 人类可读的 plan mode 推荐理由

### Manual Memory Protocol（v0.8.0+）

记忆系统不是自动的——Kamaji 必须在正确的时机主动调用 memory tools：

- 对话开始时 → `memory_recall_agent(agent="kamaji", ...)`
- 派工前 → `memory_recall_agent(agent="nekobasu", ...)` + `memory_search(...)`
- 关键决策后 → `memory_store_decision(...)`

### 示例效果（coding 团队）

```
用户：实现用户登录功能
kamaji：🌆 复杂任务，开始协调团队...

[调用 workflow 生成计划]
[调用 tasogare 规划 JWT 方案]
[调用 nekobasu 探索现有代码]
[调用 calcifer 实现登录接口]
[调用 enma 审查通过]

结果：已实现 JWT 登录系统
---
◕‿◕ Workers Involved:
- 🌆 tasogare: 规划 JWT 方案
- 🚌 nekobasu: 找到现有用户模型
- 🔥 calcifer: 实现 4 个文件
- 👹 enma: 审查通过
```

### 测试分层

- `tests/unit/` — 单元测试
- `tests/integration/` — 集成测试

```bash
make test        # 运行全部测试
make check       # 运行代码检查
```

## 链接

- [Changelog](./CHANGELOG.md)
- [License](./LICENSE)
