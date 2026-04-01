# kimi-tachi Hooks 集成指南

> 与 kimi-cli 1.28.0+ Hooks 系统的集成方案

## 概述

kimi-cli 1.28.0 引入了 **Hooks 系统** (Beta)，允许在 Agent 生命周期的关键点执行自定义命令。kimi-tachi 可以利用此系统实现自动观察、追踪和记忆功能。

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
| `SessionStart` | 会话创建/恢复时 | 自动 recall 上下文 |
| `SessionEnd` | 会话关闭时 | 存储 session 摘要 |
| `SubagentStart` | 子代理启动时 | 开始追踪 span |
| `SubagentStop` | 子代理结束时 | 结束追踪 span、存储决策 |
| `PreCompact` | 上下文压缩前 | 记录压缩原因 |
| `PostCompact` | 上下文压缩后 | 更新记忆索引 |
| `Notification` | 通知送达时 | 桌面通知、外部告警 |

## kimi-tachi Hooks 策略

### 推荐配置

在 `~/.kimi/config.toml` 中添加：

```toml
# 自动记录 Agent 调用到追踪系统
[[hooks]]
event = "SubagentStart"
command = "kimi-tachi hooks trace-start --agent {{agent_name}} --prompt '{{prompt}}'"
timeout = 5

[[hooks]]
event = "SubagentStop"
command = "kimi-tachi hooks trace-stop --agent {{agent_name}} --response '{{response}}'"
timeout = 5

# 自动存储关键决策
[[hooks]]
event = "PostToolUse"
matcher = "Agent"
command = "kimi-tachi hooks store-decision --tool-call-id {{tool_call_id}}"
timeout = 10

# Session 开始时自动 recall 上下文
[[hooks]]
event = "SessionStart"
command = "kimi-tachi hooks recall-context --source {{source}}"
timeout = 10

# Session 结束时存储摘要
[[hooks]]
event = "SessionEnd"
command = "kimi-tachi hooks store-session --reason {{reason}}"
timeout = 10

# 检查未完成的 todo
[[hooks]]
event = "Stop"
command = "kimi-tachi hooks check-todos"
timeout = 5
```

### 事件载荷示例

#### SubagentStart
```json
{
  "hook_event_name": "SubagentStart",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "agent_name": "nekobasu",
  "prompt": "Find auth-related files"
}
```

#### PostToolUse (Agent tool)
```json
{
  "hook_event_name": "PostToolUse",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "tool_name": "Agent",
  "tool_input": {
    "description": "nekobasu explores auth",
    "prompt": "Find auth files",
    "subagent_type": "nekobasu"
  },
  "tool_output": "...",
  "tool_call_id": "call_123"
}
```

## 实现路线图

### Phase 1: 基础集成 (v0.5.1)

- [ ] 提供 Hooks 配置模板
- [ ] 文档说明如何手动配置
- [ ] 示例 hooks 脚本

### Phase 2: CLI 集成 (v0.6.0)

- [ ] `kimi-tachi hooks install` - 自动安装 hooks 配置
- [ ] `kimi-tachi hooks trace-start/stop` - 追踪命令
- [ ] `kimi-tachi hooks store-decision` - 存储决策
- [ ] `kimi-tachi hooks recall-context` - 召回上下文

### Phase 3: 自动观察 (v0.6.0+)

- [ ] 自动 workflow 追踪
- [ ] 智能决策存储
- [ ] 个性化工作流学习

## 示例 Hooks 脚本

### 1. 自动追踪 Agent 调用

```bash
#!/bin/bash
# ~/.kimi/hooks/trace-agent.sh

read JSON
EVENT=$(echo "$JSON" | jq -r '.hook_event_name')
AGENT=$(echo "$JSON" | jq -r '.agent_name')
SESSION=$(echo "$JSON" | jq -r '.session_id')

if [ "$EVENT" = "SubagentStart" ]; then
    echo "[kimi-tachi] Agent started: $AGENT" >&2
    # 记录到追踪系统
    echo "$JSON" >> ~/.kimi-tachi/traces/$(date +%Y%m%d).jsonl
elif [ "$EVENT" = "SubagentStop" ]; then
    echo "[kimi-tachi] Agent completed: $AGENT" >&2
fi

exit 0
```

### 2. 检查未完成的 Todo

```bash
#!/bin/bash
# ~/.kimi/hooks/check-todos.sh

# 检查是否有未完成的 todo
if grep -q '"status": "pending"' ~/.kimi-tachi/memory/todos.json 2>/dev/null; then
    echo "⚠️  You have unfinished todos. Use /todo to check them." >&2
    # 不阻止，只是提醒
fi

exit 0
```

### 3. 保护敏感文件

```bash
#!/bin/bash
# ~/.kimi/hooks/protect-sensitive.sh

read JSON
TOOL=$(echo "$JSON" | jq -r '.tool_name')
FILE=$(echo "$JSON" | jq -r '.tool_input.file_path // empty')

# 阻止直接修改敏感文件
if [ "$TOOL" = "WriteFile" ] || [ "$TOOL" = "StrReplaceFile" ]; then
    if echo "$FILE" | grep -qE '\.env$|\.env\.local$|\.ssh/|\.aws/'; then
        echo "❌ Direct modification of $FILE is not allowed." >&2
        exit 2
    fi
fi

exit 0
```

## 配置验证

配置 hooks 后，使用以下命令验证：

```bash
# 在 kimi shell 中查看已配置的 hooks
/hooks

# 预期输出:
# Configured Hooks:
#   SubagentStart: 1 hook(s)
#   SubagentStop: 1 hook(s)
#   PostToolUse: 1 hook(s)
```

## 注意事项

1. **Beta 特性**: Hooks 系统目前是 Beta，API 可能变化
2. **Fail-Open**: Hooks 执行失败（超时、崩溃）默认允许操作
3. **超时**: 建议设置合理的 timeout（5-30 秒）
4. **性能**: 多个 hooks 并行执行，相同命令自动去重

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

---

*「さあ、働け！働け！」- Kamaji*
