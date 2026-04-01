#!/bin/bash
# kimi-tachi Agent 追踪 Hook
# 
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "SubagentStart"
# command = "/path/to/kimi-tachi/hooks/trace-agent.sh"
# timeout = 5
#
# [[hooks]]
# event = "SubagentStop"
# command = "/path/to/kimi-tachi/hooks/trace-agent.sh"
# timeout = 5

read JSON

EVENT=$(echo "$JSON" | jq -r '.hook_event_name')
AGENT=$(echo "$JSON" | jq -r '.agent_name // "unknown"')
SESSION=$(echo "$JSON" | jq -r '.session_id // "unknown"')
CWD=$(echo "$JSON" | jq -r '.cwd // "."')

# 确保追踪目录存在
TRACE_DIR="${HOME}/.kimi-tachi/traces"
mkdir -p "$TRACE_DIR"

# 按日期记录
TRACE_FILE="$TRACE_DIR/$(date +%Y%m%d).jsonl"

# 添加时间戳并记录
echo "$JSON" | jq -c '. + {recorded_at: now}' >> "$TRACE_FILE"

# 输出日志（可选）
if [ "$EVENT" = "SubagentStart" ]; then
    PROMPT=$(echo "$JSON" | jq -r '.prompt // ""' | head -c 50)
    echo "[kimi-tachi] 🚌 Agent '$AGENT' started: ${PROMPT}..." >&2
elif [ "$EVENT" = "SubagentStop" ]; then
    echo "[kimi-tachi] ✅ Agent '$AGENT' completed" >&2
fi

exit 0
