#!/bin/bash
# kimi-tachi SessionEnd Hook - 会话结束时自动总结
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "SessionEnd"
# command = "/path/to/kimi-tachi/hooks/summarize-on-end.sh"
# timeout = 15
#
# 功能:
# - 生成会话总结
# - 存储关键决策到记忆
# - 清理临时数据

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIMI_TACHI_DIR="$(dirname "$SCRIPT_DIR")"

# 从 stdin 读取事件数据
read -r EVENT_DATA

# 提取关键字段
if command -v jq &> /dev/null; then
    SESSION_ID=$(echo "$EVENT_DATA" | jq -r '.session_id // empty')
    REASON=$(echo "$EVENT_DATA" | jq -r '.reason // "unknown"')
else
    SESSION_ID=$(echo "$EVENT_DATA" | grep -o '"session_id"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    REASON=$(echo "$EVENT_DATA" | grep -o '"reason"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
fi

# 默认值
SESSION_ID=${SESSION_ID:-$(date +%s)}
REASON=${REASON:-"unknown"}

# 存储目录
STORAGE_DIR="${HOME}/.kimi-tachi/memory/hooks"
mkdir -p "$STORAGE_DIR"

# 记录日志
LOG_FILE="$STORAGE_DIR/session.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SessionEnd: session=$SESSION_ID reason=$REASON" >> "$LOG_FILE"

# ============================================================================
# 生成会话总结
# ============================================================================

SESSION_FILE="$STORAGE_DIR/session_${SESSION_ID}.json"
SUMMARY=""

if [ -f "$SESSION_FILE" ]; then
    if command -v jq &> /dev/null; then
        # 提取统计信息
        STARTED_AT=$(jq -r '.started_at // empty' "$SESSION_FILE")
        DECISIONS_COUNT=$(jq '.decisions | length' "$SESSION_FILE")
        EVENTS_COUNT=$(jq '.events | length' "$SESSION_FILE")
        COMPACT_COUNT=$(jq '.compactions | length' "$SESSION_FILE")
        
        # 计算时长
        if [ -n "$STARTED_AT" ]; then
            # 尝试计算时长（简化版）
            ENDED_AT=$(date -Iseconds)
            # 这里简化处理，实际应该用更精确的计算
        fi
        
        # 生成总结
        SUMMARY="Session Summary ($SESSION_ID):
- Duration: ended at $(date '+%H:%M')
- Decisions made: $DECISIONS_COUNT
- Events recorded: $EVENTS_COUNT
- Context compactions: $COMPACT_COUNT
- End reason: $REASON
"
        
        # 添加关键决策摘要
        if [ "$DECISIONS_COUNT" -gt 0 ]; then
            SUMMARY="${SUMMARY}
Key decisions:
"
            KEY_DECISIONS=$(jq -r '.decisions[-5:][] | "- " + .content[:80]' "$SESSION_FILE" 2>/dev/null)
            SUMMARY="${SUMMARY}${KEY_DECISIONS}
"
        fi
        
        # 保存总结到会话文件
        jq --arg summary "$SUMMARY" --arg ended_at "$(date -Iseconds)" \
           '. + {summary: $summary, ended_at: $ended_at, end_reason: "'"$REASON"'"}' \
           "$SESSION_FILE" > "${SESSION_FILE}.tmp" && mv "${SESSION_FILE}.tmp" "$SESSION_FILE"
    fi
    
    # 归档到历史目录
    HISTORY_DIR="$STORAGE_DIR/history"
    mkdir -p "$HISTORY_DIR"
    
    # 按日期归档
    DATE_PREFIX=$(date +%Y%m%d)
    cp "$SESSION_FILE" "$HISTORY_DIR/session_${DATE_PREFIX}_${SESSION_ID}.json"
    
    # 清理：保留最近30天的活跃会话，其他的移到历史
    find "$STORAGE_DIR" -name "session_*.json" -maxdepth 1 -mtime +7 -exec mv {} "$HISTORY_DIR/" \; 2>/dev/null || true
fi

# ============================================================================
# 使用 Python 工具处理
# ============================================================================

PYTHON_TOOLS="$KIMI_TACHI_DIR/src/kimi_tachi/hooks/tools.py"
if [ -f "$PYTHON_TOOLS" ]; then
    export KIMI_TACHI_MEMORY_PATH="${HOME}/.kimi-tachi/memory"
    
    echo "$EVENT_DATA" | python3 -m kimi_tachi.hooks summarize-on-end \
        session_id="$SESSION_ID" \
        reason="$REASON" 2>> "$LOG_FILE" || true
fi

# ============================================================================
# 输出总结（会被 kimi-cli 记录）
# ============================================================================

if [ -n "$SUMMARY" ]; then
    echo "
[kimi-tachi] 💾 Session saved. Summary:
$SUMMARY
" >&2
fi

# 返回成功
exit 0
