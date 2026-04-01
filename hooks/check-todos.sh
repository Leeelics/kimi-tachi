#!/bin/bash
# kimi-tachi Todo 检查 Hook
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "Stop"
# command = "/path/to/kimi-tachi/hooks/check-todos.sh"
# timeout = 5

read JSON

# 检查是否有未完成的 todo
TODO_FILE="${HOME}/.kimi-tachi/memory/todos.json"

if [ -f "$TODO_FILE" ]; then
    # 检查是否有 pending 状态的 todo
    PENDING_COUNT=$(jq '[.todos[] | select(.status == "pending")] | length' "$TODO_FILE" 2>/dev/null || echo "0")
    
    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo "" >&2
        echo "⚠️  kimi-tachi reminder: You have $PENDING_COUNT unfinished todo(s)." >&2
        echo "   Use /todo to check them before starting a new task." >&2
        echo "" >&2
    fi
fi

exit 0
