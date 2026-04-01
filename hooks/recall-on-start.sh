#!/bin/bash
# kimi-tachi SessionStart Hook - 会话开始时自动回忆
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "SessionStart"
# command = "/path/to/kimi-tachi/hooks/recall-on-start.sh"
# timeout = 10
#
# 功能:
# - 会话开始时回忆之前的上下文
# - 恢复未完成的 todo
# - 输出到 stdout（会被 kimi-cli 添加到对话上下文）

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIMI_TACHI_DIR="$(dirname "$SCRIPT_DIR")"

# 从 stdin 读取事件数据
read -r EVENT_DATA

# 提取关键字段
if command -v jq &> /dev/null; then
    SESSION_ID=$(echo "$EVENT_DATA" | jq -r '.session_id // empty')
    SOURCE=$(echo "$EVENT_DATA" | jq -r '.source // "startup"')
    CWD=$(echo "$EVENT_DATA" | jq -r '.cwd // "."')
else
    SESSION_ID=$(echo "$EVENT_DATA" | grep -o '"session_id"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    SOURCE=$(echo "$EVENT_DATA" | grep -o '"source"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    CWD=$(echo "$EVENT_DATA" | grep -o '"cwd"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
fi

# 默认值
SESSION_ID=${SESSION_ID:-$(date +%s)}
SOURCE=${SOURCE:-"startup"}
CWD=${CWD:-"."}

# 存储目录
STORAGE_DIR="${HOME}/.kimi-tachi/memory/hooks"
mkdir -p "$STORAGE_DIR"

# 记录日志
LOG_FILE="$STORAGE_DIR/session.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SessionStart: session=$SESSION_ID source=$SOURCE" >> "$LOG_FILE"

# ============================================================================
# 输出回忆内容（会被 kimi-cli 添加到对话上下文）
# ============================================================================

OUTPUT=""

# 1. 如果是恢复会话，显示之前的上下文
if [ "$SOURCE" = "resume" ]; then
    SESSION_FILE="$STORAGE_DIR/session_${SESSION_ID}.json"
    
    if [ -f "$SESSION_FILE" ]; then
        # 有之前的会话数据
        OUTPUT="${OUTPUT}
📚 **Context from previous session:**

"
        
        # 提取最近的决策（使用 jq 如果可用）
        if command -v jq &> /dev/null; then
            DECISIONS=$(jq -r '.decisions[-3:][] | "• " + .content' "$SESSION_FILE" 2>/dev/null || echo "")
            if [ -n "$DECISIONS" ]; then
                OUTPUT="${OUTPUT}**Recent decisions:**
${DECISIONS}

"
            fi
            
            # 提取 Agent 调用
            AGENT_CALLS=$(jq -r '[.events[] | select(.type == "agent_call")][-3:] | .[] | "• Used: " + .agent' "$SESSION_FILE" 2>/dev/null || echo "")
            if [ -n "$AGENT_CALLS" ]; then
                OUTPUT="${OUTPUT}**Agent activity:**
${AGENT_CALLS}

"
            fi
            
            # 提取压缩历史
            COMPACT_COUNT=$(jq '.compactions | length' "$SESSION_FILE" 2>/dev/null || echo "0")
            if [ "$COMPACT_COUNT" -gt 0 ]; then
                OUTPUT="${OUTPUT}*Note: Context was compacted $COMPACT_COUNT time(s) in previous session*

"
            fi
        fi
        
        OUTPUT="${OUTPUT}---
"
    fi
fi

# 2. 检查是否有未完成的 todo
TODO_FILE="${HOME}/.kimi-tachi/memory/todos.json"
if [ -f "$TODO_FILE" ]; then
    if command -v jq &> /dev/null; then
        PENDING_COUNT=$(jq '[.todos[]? | select(.status == "pending")] | length' "$TODO_FILE" 2>/dev/null || echo "0")
        IN_PROGRESS_COUNT=$(jq '[.todos[]? | select(.status == "in_progress")] | length' "$TODO_FILE" 2>/dev/null || echo "0")
        
        if [ "$PENDING_COUNT" -gt 0 ] || [ "$IN_PROGRESS_COUNT" -gt 0 ]; then
            OUTPUT="${OUTPUT}
📋 **Active todos:**

"
            
            if [ "$IN_PROGRESS_COUNT" -gt 0 ]; then
                IN_PROGRESS=$(jq -r '.todos[]? | select(.status == "in_progress") | "• [🔄] " + .title' "$TODO_FILE" 2>/dev/null)
                OUTPUT="${OUTPUT}${IN_PROGRESS}

"
            fi
            
            if [ "$PENDING_COUNT" -gt 0 ]; then
                PENDING=$(jq -r '.todos[]? | select(.status == "pending") | "• [⏳] " + .title' "$TODO_FILE" 2>/dev/null | head -5)
                OUTPUT="${OUTPUT}${PENDING}

"
                
                if [ "$PENDING_COUNT" -gt 5 ]; then
                    OUTPUT="${OUTPUT}*... and $((PENDING_COUNT - 5)) more pending*

"
                fi
            fi
            
            OUTPUT="${OUTPUT}---
"
        fi
    fi
fi

# 3. 输出到 stdout（kimi-cli 会捕获并添加到上下文）
if [ -n "$OUTPUT" ]; then
    echo "$OUTPUT"
fi

# 4. 使用 Python 工具保存会话数据
PYTHON_TOOLS="$KIMI_TACHI_DIR/src/kimi_tachi/hooks/tools.py"
if [ -f "$PYTHON_TOOLS" ]; then
    export KIMI_TACHI_MEMORY_PATH="${HOME}/.kimi-tachi/memory"
    
    echo "$EVENT_DATA" | python3 -m kimi_tachi.hooks recall-on-start \
        session_id="$SESSION_ID" \
        source="$SOURCE" \
        cwd="$CWD" 2>> "$LOG_FILE" || true
fi

# 返回成功
exit 0
