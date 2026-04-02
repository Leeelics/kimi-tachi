# kimi-tachi Hooks

> 与 kimi-cli 1.28.0+ Hooks 系统的集成脚本

## 快速开始

```bash
# 1. 安装 hooks 到 kimi-cli
kimi-tachi install  # 或手动复制 hooks/ 目录到 ~/.kimi/agents/kimi-tachi/

# 2. 合并配置到 ~/.kimi/config.toml
cat hooks/config.toml.example >> ~/.kimi/config.toml
# 然后编辑修改路径

# 3. 验证安装
kimi
> /hooks
```

## Git Hooks

### pre-push

自动在 push 前运行完整的 CI 检查，确保代码质量：

```bash
# 安装 pre-push hook
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# 现在每次 git push 都会自动检查
# 检查失败会阻止 push
```

**检查内容（5步）：**

| 步骤 | 命令 | 说明 | 可跳过 |
|------|------|------|--------|
| 1 | `make check` | Lint 和格式检查 | `SKIP_LINT=1` |
| 2 | `make test` | 运行所有测试 | `SKIP_TESTS=1` |
| 3 | `scripts/check_version.py` | 版本一致性检查 | - |
| 4 | `make changelog-check` | CHANGELOG 更新检查 | - |
| 5 | `make build` + `make build-check` | 打包和安装测试 | `SKIP_BUILD=1` |

**快速 push（跳过耗时检查）：**
```bash
# 仅跳过 build（推荐用于日常开发）
SKIP_BUILD=1 git push

# 跳过多个检查
SKIP_BUILD=1 SKIP_TESTS=1 git push

# 完全跳过所有检查（紧急情况下）
git push --no-verify
```

> ⚠️ **注意**：`--no-verify` 会跳过所有检查，可能导致 CI 失败。建议仅在紧急修复时使用。

## kimi-cli Hooks

| Hook | 事件 | 功能 |
|------|------|------|
| `trace-agent.sh` | SubagentStart/Stop | 自动记录 Agent 调用追踪 |
| `check-todos.sh` | Stop | 提醒未完成的 todo |
| `protect-sensitive.sh` | PreToolUse | 阻止修改敏感文件 |

## 配置说明

编辑 `~/.kimi/config.toml`：

```toml
[[hooks]]
event = "SubagentStart"
command = "/path/to/kimi-tachi/hooks/trace-agent.sh"
timeout = 5
```

## 自定义 Hooks

1. 创建脚本（参考现有脚本）
2. 设置可执行权限：`chmod +x your-hook.sh`
3. 添加到 `~/.kimi/config.toml`
4. 重启 kimi-cli

## 调试

```bash
# 查看追踪记录
cat ~/.kimi-tachi/traces/$(date +%Y%m%d).jsonl

# 测试 hook 脚本
echo '{"hook_event_name":"SubagentStart","agent_name":"test"}' | ./hooks/trace-agent.sh
```

## 更多信息

- [完整文档](../docs/HOOKS_INTEGRATION.md)
- [kimi-cli Hooks 文档](https://github.com/moonshot-ai/Kimi-CLI/blob/main/docs/hooks.md)
