# Hooks Integration (Legacy → Native)

> **Status (v0.8.0+)**: The old shell-hook based automatic memory system has been removed.  
> Kimi-tachi now relies on **kimi-cli's native hook engine** and **manual memory tools**.

## What Changed

In previous versions, kimi-tachi shipped shell scripts (`recall-on-start.sh`, `store-before-compact.sh`, etc.) that tried to implement automatic memory by writing custom JSON files. These scripts:
- Referenced a Python module (`kimi_tachi.hooks`) that no longer exists
- Created a parallel state store (`~/.kimi-tachi/memory/hooks/`) disconnected from kimi-cli's native runtime
- Conflicted with kimi-cli's own `HookEngine`, `SubagentStore`, and `BackgroundTaskStore`

**All of these shell scripts have been deleted in v0.8.0.**

## Recommended Approach

### 1. Use Native `Agent()` Orchestration

Kamaji (the root agent) should use kimi-cli native tools directly:
- `Agent(subagent_type=...)` for worker delegation
- `SetTodoList()` for progress tracking
- `TaskList()` / `TaskOutput()` for background task monitoring
- `ExitPlanMode()` for plan checkpoints

See `agents/coding/kamaji.yaml` for the complete Native Tool Orchestration Protocol.

### 2. Use Manual Memory Tools

When you need cross-session or cross-project memory, call the plugin tools explicitly:

```python
# Before delegating
memory_recall_agent(agent="kamaji", task="{task description}")

# After key decisions
memory_store_decision(
    content="Use Redis for session storage",
    category="architecture",
    tags=["auth", "redis"]
)
```

### 3. (Optional) Configure kimi-cli Native Hooks

If you still want automated hooks (e.g. recall on session start), use kimi-cli's native `config.toml` hook system:

```toml
[[hooks]]
event = "SessionStart"
command = ["python3", "-m", "kimi_tachi.cli", "memory-recall"]
timeout = 30
```

Note: Any native hook should call a **supported plugin tool** or CLI command — not the deleted `kimi_tachi.hooks` module.

## Migration Checklist

- [ ] Remove any `~/.kimi/config.toml` entries pointing to `hooks/recall-on-start.sh` or similar deleted scripts
- [ ] Delete stale `~/.kimi-tachi/memory/hooks/` JSON files (they are no longer read by any tool)
- [ ] Update custom agent specs to use the manual memory protocol in `kamaji.yaml`
