#!/bin/bash
# kimi-tachi 敏感文件保护 Hook
#
# 安装: 添加到 ~/.kimi/config.toml
# [[hooks]]
# event = "PreToolUse"
# matcher = "WriteFile|StrReplaceFile"
# command = "/path/to/kimi-tachi/hooks/protect-sensitive.sh"
# timeout = 5

read JSON

TOOL=$(echo "$JSON" | jq -r '.tool_name')
FILE=$(echo "$JSON" | jq -r '.tool_input.file_path // empty')

# 敏感文件模式
SENSITIVE_PATTERNS='\.env$|\.env\.local$|\.env\.[a-zA-Z]+$|\.ssh/|\.aws/|\.docker/|\.kube/|id_rsa|id_dsa|id_ecdsa|id_ed25519'

if [ -n "$FILE" ]; then
    if echo "$FILE" | grep -qE "$SENSITIVE_PATTERNS"; then
        echo "" >&2
        echo "❌ kimi-tachi Security Alert:" >&2
        echo "   Direct modification of '$FILE' is not allowed." >&2
        echo "   This file may contain sensitive data (passwords, keys, tokens)." >&2
        echo "" >&2
        echo "   Suggested alternatives:" >&2
        echo "   - Edit .env.example instead" >&2
        echo "   - Use environment variable injection" >&2
        echo "   - Use a secrets management tool" >&2
        echo "" >&2
        exit 2
    fi
fi

exit 0
