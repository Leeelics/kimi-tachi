#!/bin/bash
# kimi-tachi PreCompact Hook - 压缩前自动存储
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "PreCompact"
# command = "/path/to/kimi-tachi/hooks/store-before-compact.sh"
# timeout = 10
#
# 功能:
# - 在上下文压缩前提取关键决策
# - 存储到 kimi-tachi 记忆系统
# - 记录压缩事件历史

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIMI_TACHI_DIR="$(dirname "$SCRIPT_DIR")"

# 从 stdin 读取事件数据
read -r EVENT_DATA

# 提取关键字段（使用 jq 如果可用，否则用简单字符串处理）
if command -v jq &> /dev/null; then
    SESSION_ID=$(echo "$EVENT_DATA" | jq -r '.session_id // empty')
    TRIGGER=$(echo "$EVENT_DATA" | jq -r '.trigger // "unknown"')
    TOKEN_COUNT=$(echo "$EVENT_DATA" | jq -r '.token_count // 0')
    CWD=$(echo "$EVENT_DATA" | jq -r '.cwd // "."')
else
    # 简单的字符串提取作为后备
    SESSION_ID=$(echo "$EVENT_DATA" | grep -o '"session_id"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    TRIGGER=$(echo "$EVENT_DATA" | grep -o '"trigger"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
    TOKEN_COUNT=$(echo "$EVENT_DATA" | grep -o '"token_count"[^,}]*' | grep -o ':[0-9]*' | tr -d ':' | head -1)
    CWD=$(echo "$EVENT_DATA" | grep -o '"cwd"[^}]*' | grep -o ':"[^"]*"' | tr -d ':"' | head -1)
fi

# 默认值
SESSION_ID=${SESSION_ID:-$(date +%s)}
TRIGGER=${TRIGGER:-"unknown"}
TOKEN_COUNT=${TOKEN_COUNT:-0}
CWD=${CWD:-"."}

# 确保存储目录存在
STORAGE_DIR="${HOME}/.kimi-tachi/memory/hooks"
mkdir -p "$STORAGE_DIR"

# 记录日志
LOG_FILE="$STORAGE_DIR/precompact.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] PreCompact: session=$SESSION_ID trigger=$TRIGGER tokens=$TOKEN_COUNT" >> "$LOG_FILE"

# 检查是否有 Python 工具可用
PYTHON_TOOLS="$KIMI_TACHI_DIR/src/kimi_tachi/hooks/tools.py"

if [ -f "$PYTHON_TOOLS" ]; then
    # 使用 Python 工具处理
    export KIMI_TACHI_MEMORY_PATH="${HOME}/.kimi-tachi/memory"
    
    # 调用 Python 工具
    echo "$EVENT_DATA" | python3 -m kimi_tachi.hooks store-before-compact \
        session_id="$SESSION_ID" \
        trigger="$TRIGGER" \
        token_count="$TOKEN_COUNT" \
        cwd="$CWD" 2>> "$LOG_FILE"
    
    RESULT=$?
    
    if [ $RESULT -eq 0 ]; then
        echo "[kimi-tachi] 💾 Key decisions stored before compact (trigger: $TRIGGER, tokens: $TOKEN_COUNT)" >&2
    else
        echo "[kimi-tachi] ⚠️ Storage failed, but continuing with compact" >&2
    fi
else
    # 简单模式：仅记录事件
    SESSION_FILE="$STORAGE_DIR/session_${SESSION_ID}.json"
    
    if [ -f "$SESSION_FILE" ]; then
        # 更新现有会话文件
        if command -v jq &> /dev/null; then
            jq ".compactions += [{\"trigger\": \"$TRIGGER\", \"token_count\": $TOKEN_COUNT, \"timestamp\": \"$(date -Iseconds)\"}]" \
               "$SESSION_FILE" > "${SESSION_FILE}.tmp" && mv "${SESSION_FILE}.tmp" "$SESSION_FILE"
        fi
    else
        # 创建新会话文件
        cat > "$SESSION_FILE" << EOF
{
  "session_id": "$SESSION_ID",
  "started_at": "$(date -Iseconds)",
  "compactions": [
    {
      "trigger": "$TRIGGER",
      "token_count": $TOKEN_COUNT,
      "timestamp": "$(date -Iseconds)"
    }
  ],
  "decisions": [],
  "events": []
}
EOF
    fi
    
    echo "[kimi-tachi] 💾 Compact recorded (simple mode)" >&2
fi

# 总是返回成功，不阻塞压缩流程
exit 0
