# Bug Report: MCP servers are duplicated when loading custom agents with subagents

## Summary
When using a custom agent YAML file with `subagents` defined, kimi-cli repeatedly spawns MCP (Model Context Protocol) server processes for each subagent, causing severe memory bloat and process leakage.

## Environment
- **OS**: Ubuntu (Linux x86_64)
- **kimi-cli version**: Latest (installed via `uv`)
- **Python version**: 3.12/3.13
- **MCP servers configured**: 
  - `@playwright/mcp@latest`
  - `@upstash/context7-mcp@latest`

## Steps to Reproduce

### Step 1: Configure MCP servers
```bash
# ~/.kimi/mcp.json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "context7": {
      "command": "npx", 
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

### Step 2: Create a custom agent with subagents
Create `~/.kimi/agents/test-agent.yaml`:
```yaml
version: 1
agent:
  name: "test-agent"
  extend: default
  system_prompt_args:
    ROLE: "Test"
  
  subagents:
    subagent1:
      path: ./subagent1.yaml
      description: "Subagent 1"
    subagent2:
      path: ./subagent2.yaml  
      description: "Subagent 2"
    # ... more subagents
```

### Step 3: Run kimi with the custom agent
```bash
kimi --agent-file ~/.kimi/agents/test-agent.yaml --print <<< "test"
```

### Step 4: Observe MCP processes
```bash
# In another terminal
ps aux | grep -E "playwright-mcp|context7-mcp" | wc -l
```

## Expected Behavior
Only **2 MCP processes** should be spawned (one for each configured MCP server), regardless of how many subagents are defined.

## Actual Behavior
**14+ MCP processes** are spawned. The number scales with the number of subagents defined in the agent YAML.

### Evidence

#### Test Results
| Scenario | MCP Process Count |
|----------|------------------|
| Default agent (no `--agent-file`) | 2-4 processes |
| Custom agent with 6 subagents | 12-16 processes |
| After multiple runs | 90+ processes (accumulated) |

#### Log Evidence
From `~/.kimi/logs/kimi.log`:
```
2026-03-18 13:07:29 | Connected MCP server: playwright
2026-03-18 13:07:32 | Connected MCP server: context7
2026-03-18 13:07:34 | Connected MCP server: context7  # Duplicate!
2026-03-18 13:07:34 | Connected MCP server: playwright # Duplicate!
2026-03-18 13:07:35 | Connected MCP server: context7  # Another duplicate!
...
```

#### Process Tree
```
kimi-tachi(15505)---Kimi Code(15506)
  ├─npm exec @playwright... (× N)  # N = number of subagents + 1
  └─npm exec @upstash... (× N)
```

## Root Cause Analysis

Based on code review of `src/kimi_cli/soul/agent.py`:

```python
# Line 276-284 in agent.py
for subagent_name, subagent_spec in agent_spec.subagents.items():
    subagent = await load_agent(
        subagent_spec.path,
        runtime.copy_for_fixed_subagent(),
        mcp_configs=mcp_configs,  # ← Problem: Same MCP configs passed to every subagent
        _restore_dynamic_subagents=False,
    )
```

The issue is in the `load_agent` function:
1. Each call to `load_agent` creates a new `KimiToolset`
2. `KimiToolset` calls `load_mcp_tools(mcp_configs, runtime)`
3. This spawns new MCP server processes for **every subagent**
4. MCP servers are not shared/reused between agent and subagents

## Impact

- **Memory**: Each MCP process uses 50-100MB RAM. With 6 subagents + 2 MCP servers = ~800MB wasted
- **CPU**: Multiple identical MCP servers competing for resources
- **Process leakage**: Old MCP processes are not cleaned up on exit
- **Startup time**: Slow agent loading due to multiple MCP handshakes

## Workarounds

### Option 1: Disable MCP servers
```bash
mv ~/.kimi/mcp.json ~/.kimi/mcp.json.bak
```

### Option 2: Remove MCP servers from config
```bash
kimi mcp remove playwright
kimi mcp remove context7
```

### Option 3: Use default agent only
Don't use `--agent-file` with custom agents that have subagents.

## Suggested Fixes

### Fix 1: Share MCP servers across agent hierarchy
Modify `load_agent` to accept an optional `shared_toolset` parameter, or cache MCP clients at the Runtime level.

### Fix 2: Lazy MCP loading
Only load MCP tools when actually needed, not during agent initialization.

### Fix 3: Process pooling
Maintain a single MCP process pool per Runtime, shared by all agents/subagents.

## Additional Context

This issue is particularly problematic for multi-agent orchestration systems (like kimi-tachi) that use custom agents with multiple subagents to delegate tasks. The current behavior makes it impossible to use MCP tools without severe resource overhead.

---

**Labels**: bug, performance, mcp, memory
**Priority**: High
