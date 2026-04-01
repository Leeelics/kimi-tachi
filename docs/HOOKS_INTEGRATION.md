# kimi-tachi Hooks 集成指南

> 与 kimi-cli 1.28.0+ Hooks 系统的集成方案
> 
> **v0.5.2 更新**: 新增自动记忆管理 Hooks

## 概述

kimi-cli 1.28.0 引入了 **Hooks 系统** (Beta)，允许在 Agent 生命周期的关键点执行自定义命令。kimi-tachi 利用此系统实现**自动记忆管理**、追踪和安全功能。

### v0.5.2 核心功能

```
┌─────────────────────────────────────────────────────────────┐
│              自动记忆管理流程 (v0.5.2)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SessionStart          PreCompact          SessionEnd       │
│       │                     │                    │          │
│       ▼                     ▼                    ▼          │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐     │
│  │ 回忆    │          │ 存储    │          │ 总结    │     │
│  │ 上下文  │          │ 决策    │          │ 归档    │     │
│  └─────────┘          └─────────┘          └─────────┘     │
│       │                     │                    │          │
│       ▼                     ▼                    ▼          │
│  加载之前              压缩前保存            生成摘要       │
│  的决策                关键信息              存储历史       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 什么是 Hooks

Hooks 是在特定事件触发时执行的 shell 命令，接收 JSON 上下文并通过标准输入传递。根据退出码决定后续行为：

| 退出码 | 行为 | 说明 |
|--------|------|------|
| `0` | 允许 | stdout 内容（如有）会添加到上下文 |
| `2` | 阻止 | stderr 内容会反馈给 LLM 作为修正 |
| 其他 | 允许 | stderr 仅记录，不展示给 LLM |

## 支持的事件类型

kimi-cli 1.28.0 支持 13 种生命周期事件：

| 事件 | 触发时机 | kimi-tachi 用途 |
|------|----------|-----------------|
| `PreToolUse` | 工具调用前 | 安全检查、权限验证 |
| `PostToolUse` | 工具成功执行后 | 记录工具使用、更新追踪 |
| `PostToolUseFailure` | 工具执行失败后 | 错误记录、故障分析 |
| `UserPromptSubmit` | 用户提交输入时 | 输入分析、模式识别 |
| `Stop` | Agent 回合结束时 | 任务完成检查、自动存储 |
| `StopFailure` | 回合因错误结束时 | 错误报告、恢复逻辑 |
| `SessionStart` | 会话创建/恢复时 | **自动 recall 上下文** ⭐ |
| `SessionEnd` | 会话关闭时 | **存储 session 摘要** ⭐ |
| `SubagentStart` | 子代理启动时 | 开始追踪 span |
| `SubagentStop` | 子代理结束时 | 结束追踪 span、存储决策 |
| `PreCompact` | 上下文压缩前 | **存储关键决策** ⭐⭐⭐ |
| `PostCompact` | 上下文压缩后 | 更新记忆索引 |
| `Notification` | 通知送达时 | 桌面通知、外部告警 |

## 快速开始

### 1. 安装 Hooks

```bash
# 确保 hooks 目录存在
ls ~/.kimi/agents/kimi-tachi/hooks/

# 检查脚本权限
ls -la ~/.kimi/agents/kimi-tachi/hooks/*.sh
```

### 2. 配置 kimi-cli

复制配置到 `~/.kimi/config.toml`：

```bash
cat ~/.kimi/agents/kimi-tachi/hooks/config.toml.example >> ~/.kimi/config.toml
# 编辑修改路径
```

### 3. 验证配置

在 kimi shell 中执行：

```
/hooks

# 预期输出：
# Configured Hooks:
#   SessionStart: 1 hook(s)
#   PreCompact: 1 hook(s)
#   SessionEnd: 1 hook(s)
#   PostToolUse: 1 hook(s)
#   SubagentStart: 1 hook(s)
#   SubagentStop: 1 hook(s)
```

## v0.5.2 自动记忆 Hooks

### 核心 Hooks

#### 1. `recall-on-start.sh` - SessionStart

**功能**: 会话开始时自动回忆上下文

**输出示例**:
```
📚 **Context from previous session:**

**Recent decisions:**
• Decided to use JWT authentication
• Chose PostgreSQL for database

**Agent activity:**
• Used: shishigami (architecture)
• Used: calcifer (implementation)

---

📋 **Active todos:**

• [🔄] Implement user login endpoint
• [⏳] Add password validation
• [⏳] Write tests for auth module

---
```

**配置**:
```toml
[[hooks]]
event = "SessionStart"
command = "/path/to/kimi-tachi/hooks/recall-on-start.sh"
timeout = 10
```

#### 2. `store-before-compact.sh` - PreCompact ⭐

**功能**: 上下文压缩前自动存储关键决策

**这是最重要的 hook**，防止重要信息在压缩中丢失。

**工作流程**:
```
上下文接近上限 → 触发 PreCompact
        ↓
提取关键决策（包含 decision/conclusion/final 的消息）
        ↓
存储到记忆系统
        ↓
kimi-cli 执行压缩
```

**配置**:
```toml
[[hooks]]
event = "PreCompact"
command = "/path/to/kimi-tachi/hooks/store-before-compact.sh"
timeout = 10
```

#### 3. `summarize-on-end.sh` - SessionEnd

**功能**: 会话结束时自动生成总结

**执行内容**:
- 统计会话数据（决策数、事件数、压缩次数）
- 生成会话摘要
- 归档到历史目录
- 清理过期数据

**配置**:
```toml
[[hooks]]
event = "SessionEnd"
command = "/path/to/kimi-tachi/hooks/summarize-on-end.sh"
timeout = 15
```

#### 4. `process-agent.sh` - PostToolUse (Agent)

**功能**: Agent 调用后自动记录

**记录内容**:
- Agent 调用事件
- 从输出中提取的决策
- 时间戳和元数据

**配置**:
```toml
[[hooks]]
event = "PostToolUse"
matcher = "Agent"
command = "/path/to/kimi-tachi/hooks/process-agent.sh"
timeout = 5
```

### 完整配置示例

```toml
# ~/.kimi/config.toml

# ============================================
# kimi-tachi 自动记忆管理 (v0.5.2)
# ============================================

# 1. 会话开始 - 回忆上下文
[[hooks]]
event = "SessionStart"
command = "~/.kimi/agents/kimi-tachi/hooks/recall-on-start.sh"
timeout = 10

# 2. 压缩前 - 存储关键决策 (最重要)
[[hooks]]
event = "PreCompact"
command = "~/.kimi/agents/kimi-tachi/hooks/store-before-compact.sh"
timeout = 10

# 3. 会话结束 - 生成总结
[[hooks]]
event = "SessionEnd"
command = "~/.kimi/agents/kimi-tachi/hooks/summarize-on-end.sh"
timeout = 15

# 4. Agent 调用后 - 记录决策
[[hooks]]
event = "PostToolUse"
matcher = "Agent"
command = "~/.kimi/agents/kimi-tachi/hooks/process-agent.sh"
timeout = 5

# 5. 追踪 Agent 调用
[[hooks]]
event = "SubagentStart"
command = "~/.kimi/agents/kimi-tachi/hooks/trace-agent.sh"
timeout = 5

[[hooks]]
event = "SubagentStop"
command = "~/.kimi/agents/kimi-tachi/hooks/trace-agent.sh"
timeout = 5

# 6. 检查未完成的 todo
[[hooks]]
event = "Stop"
command = "~/.kimi/agents/kimi-tachi/hooks/check-todos.sh"
timeout = 5

# 7. 保护敏感文件
[[hooks]]
event = "PreToolUse"
matcher = "WriteFile|StrReplaceFile"
command = "~/.kimi/agents/kimi-tachi/hooks/protect-sensitive.sh"
timeout = 5
```

## 事件载荷示例

### SessionStart
```json
{
  "hook_event_name": "SessionStart",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "source": "startup"
}
```

### PreCompact
```json
{
  "hook_event_name": "PreCompact",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "trigger": "token_limit",
  "token_count": 15000
}
```

### SessionEnd
```json
{
  "hook_event_name": "SessionEnd",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "reason": "user_exit"
}
```

## 数据存储

### 会话数据存储路径

```
~/.kimi-tachi/memory/hooks/
├── session_<id>.json          # 当前活跃会话
├── session_<id>.json          # 其他活跃会话
├── history/                   # 归档的历史会话
│   ├── session_20260401_abc.json
│   └── session_20260401_def.json
├── precompact.log             # PreCompact 操作日志
├── session.log                # 会话事件日志
└── agent.log                  # Agent 调用日志
```

### 会话数据结构

```json
{
  "session_id": "abc123",
  "started_at": "2026-04-01T12:00:00",
  "ended_at": "2026-04-01T14:30:00",
  "source": "startup",
  "cwd": "/home/user/project",
  "decisions": [
    {
      "type": "decision",
      "content": "Use JWT authentication",
      "timestamp": "2026-04-01T12:15:00"
    }
  ],
  "events": [
    {
      "type": "agent_call",
      "agent": "shishigami",
      "timestamp": "2026-04-01T12:10:00"
    }
  ],
  "compactions": [
    {
      "trigger": "token_limit",
      "token_count": 15000,
      "timestamp": "2026-04-01T13:00:00"
    }
  ],
  "summary": "Session Summary: ..."
}
```

## 实现路线图

### ✅ Phase 1: 自动记忆 (v0.5.2) - 已完成

- [x] `recall-on-start.sh` - 自动回忆上下文
- [x] `store-before-compact.sh` - 压缩前存储决策
- [x] `summarize-on-end.sh` - 会话总结
- [x] `process-agent.sh` - Agent 决策记录
- [x] Python 工具模块 (`kimi_tachi/hooks/tools.py`)
- [x] 完整配置模板

### Phase 2: 增强功能 (v0.6.0)

- [ ] `kimi-tachi hooks install` - 自动安装配置
- [ ] 智能上下文选择（基于语义相似度）
- [ ] 跨会话上下文继承
- [ ] Token 预算管理

### Phase 3: 高级功能 (v0.7.0+)

- [ ] 个性化工作流学习
- [ ] 自动决策分类
- [ ] 记忆重要性评估
- [ ] 长期趋势分析

## 故障排除

### 检查 Hook 是否执行

```bash
# 查看日志
tail -f ~/.kimi-tachi/memory/hooks/session.log
tail -f ~/.kimi-tachi/memory/hooks/precompact.log

# 检查会话数据
ls -la ~/.kimi-tachi/memory/hooks/
cat ~/.kimi-tachi/memory/hooks/session_*.json
```

### Hook 超时

如果 hook 经常超时：
1. 增加 `timeout` 值（默认 5-15 秒）
2. 检查磁盘空间
3. 简化 hook 逻辑

### 权限问题

```bash
# 确保脚本可执行
chmod +x ~/.kimi/agents/kimi-tachi/hooks/*.sh

# 确保目录可写
mkdir -p ~/.kimi-tachi/memory/hooks
touch ~/.kimi-tachi/memory/hooks/test && rm ~/.kimi-tachi/memory/hooks/test
```

## 注意事项

1. **Beta 特性**: Hooks 系统目前是 Beta，API 可能变化
2. **Fail-Open**: Hooks 执行失败（超时、崩溃）默认允许操作，不会阻塞主流程
3. **幂等性**: 自动记忆 hooks 设计为幂等，多次执行不会重复存储
4. **性能**: 多个 hooks 并行执行，相同命令自动去重
5. **隐私**: 会话数据存储在本地，不会上传到云端

## 与 Plugins 的区别

| 特性 | Hooks | Plugins |
|------|-------|---------|
| 触发时机 | 生命周期事件 | 工具调用 |
| 交互方式 | 无交互，接收 stdin | 接收 JSON 参数 |
| 用途 | 自动化、安全、通知 | 扩展 AI 能力 |
| 返回值 | 退出码控制流程 | stdout 作为结果 |

## 相关文档

- [kimi-cli Hooks 文档](https://github.com/moonshot-ai/Kimi-CLI/blob/main/docs/hooks.md)
- [kimi-tachi VISION.md](./VISION.md)
- [kimi-tachi ROADMAP.md](./ROADMAP.md)
- [kimi-tachi Memory Guide](./MEMORY_TEST_GUIDE.md)

---

*「さあ、働け！働け！」- Kamaji*
