#!/bin/bash
# kimi-tachi PostToolUse Hook (Agent) - Agent 调用后自动处理
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "PostToolUse"
# matcher = "Agent"
# command = "/path/to/kimi-tachi/hooks/process-agent.sh"
# timeout = 5
#
# 功能:
# - 记录 Agent 调用事件
# - 提取并存储关键决策
# - 更新会话状态

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIMI_TACHI_DIR="$(dirname "$SCRIPT_DIR")"

# 从 stdin 读取事件数据
read -r EVENT_DATA

# 提取关键字段
if command -v jq &> /dev/null; then
    SESSION_ID=$(echo "$EVENT_DATA" | jq -r '.session_id // empty')
    TOOL_NAME=$(echo "$EVENT_DATA" | jq -r '.tool_name // empty')
    TOOL_CALL_ID=$(echo "$EVENT_DATA" | jq -r '.tool_call_id // empty')
    
    # 提取 tool_input 和 tool_output
    SUBAGENT_TYPE=$(echo "$EVENT_DATA" | jq -r '.tool_input.subagent_type // "coder"')
    DESCRIPTION=$(echo "$EVENT_DATA" | jq -r '.tool_input.description // ""')
    TOOL_OUTPUT=$(echo "$EVENT_DATA" | jq -r '.tool_output // ""')
else
    SESSION_ID=$(echo "$EVENT_DATA" | grep -o '"session_id"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    SUBAGENT_TYPE="coder"
    DESCRIPTION=""
    TOOL_OUTPUT=""
fi

# 默认值
SESSION_ID=${SESSION_ID:-$(date +%s)}
SUBAGENT_TYPE=${SUBAGENT_TYPE:-"coder"}

# 存储目录
STORAGE_DIR="${HOME}/.kimi-tachi/memory/hooks"
mkdir -p "$STORAGE_DIR"

# 记录日志
LOG_FILE="$STORAGE_DIR/agent.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent: session=$SESSION_ID agent=$SUBAGENT_TYPE" >> "$LOG_FILE"

# ============================================================================
# 使用 Python 工具处理
# ============================================================================

PYTHON_TOOLS="$KIMI_TACHI_DIR/src/kimi_tachi/hooks/tools.py"
if [ -f "$PYTHON_TOOLS" ]; then
    export KIMI_TACHI_MEMORY_PATH="${HOME}/.kimi-tachi/memory"
    
    # 构建 JSON 输入
    JSON_INPUT=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "agent_name": "$SUBAGENT_TYPE",
  "tool_input": {
    "description": "$DESCRIPTION",
    "subagent_type": "$SUBAGENT_TYPE"
  },
  "tool_output": $(echo "$TOOL_OUTPUT" | jq -R -s . 2>/dev/null || echo '""')
}
EOF
)
    
    echo "$JSON_INPUT" | python3 -m kimi_tachi.hooks process-agent \
        session_id="$SESSION_ID" \
        agent_name="$SUBAGENT_TYPE" 2>> "$LOG_FILE" || true
else
    # 简单模式：直接更新会话文件
    SESSION_FILE="$STORAGE_DIR/session_${SESSION_ID}.json"
    
    if [ -f "$SESSION_FILE" ] && command -v jq &> /dev/null; then
        jq ".events += [{\"type\": \"agent_call\", \"agent\": \"$SUBAGENT_TYPE\", \"timestamp\": \"$(date -Iseconds)\"}]" \
           "$SESSION_FILE" > "${SESSION_FILE}.tmp" && mv "${SESSION_FILE}.tmp" "$SESSION_FILE"
    fi
fi

# 返回成功（不阻塞主流程）
exit 0
