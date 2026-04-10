# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-04-10

### Added
- **Workflow Plan Enhancements**: `workflow.py` now outputs additional kimi-cli 1.30.0+ capabilities:
  - `model` override per phase (`shishigami` automatically recommends `kimi-k2.5`)
  - `resume` flag for consecutive identical-agent phases
  - `plan_mode_reason` in recommendations with human-readable justification
- **Efficiency Benchmark**: Added `BENCHMARK.md` and `scripts/evaluate_cleanup.py` for tracking project health, test density, and capability gaps

### Changed
- **Massive Dead-Code Removal**: Removed legacy orchestrator, context, tracing, vis, session, and background modules (~15,000 lines deleted)
- Project is now a focused **Plan Generator** thin layer rather than an execution engine

### Fixed
- **Subagent Type Mapping**: `workflow.py` now emits native `coder`/`explore`/`plan` types instead of anime character names

## [0.7.1] - 2026-04-10

### Fixed
- **Team Manager Path Resolution**: Fixed `_get_agent_file` and `_list_available_agents` to resolve agent YAMLs relative to the same base directory as `teams.yaml`, ensuring compatibility with both wheel installs and editable installs
- **Release Workflow**: Fixed `validate` job missing `uv` installation and corrected `changelog-check` target in Makefile

## [0.7.0] - 2026-04-10

### Changed
- **Install Behavior**: `kimi-tachi install` now upgrades existing files by default (overwrites old installs)
- **New CLI Option**: Added `--skip-existing` flag to `install` command to preserve existing files

### Fixed
- **Lint**: Fixed ruff import order and unused import errors in `scripts/check_changelog.py`

## [0.6.2] - 2026-04-10

### Changed
- **CLI Refactoring**: Simplified CLI structure by removing deprecated commands (`setup`, `run`, `do`, `list_agents`, `memory`, `reset`, `workflow`, `sessions`, `traces`)
- **Test Suite Reorganization**: Split tests into `tests/unit/` and `tests/integration/` layers

### Added
- **CLI Tests**: Added comprehensive unit tests for simplified CLI surface (`install`, `uninstall`, `teams`, `status`, `_resolve_data_dir`)

## [0.6.1] - 2026-04-09

### Changed
- **Content Team Refactoring**:
  - Added `COORDINATOR_PROTOCOL` to `xunyu.yaml` enforcing foreground execution mode
  - Simplified content team workers (`guojia`, `chenlin`, `zhugeliang`, `zhugejin`)
  - Removed redundant rules from workers, centralizing control in coordinator
  - Workers now focus on execution only, coordinator controls workflow
  - Net reduction of ~150 lines across 5 agent files

### Added
- `data/` directory added to `.gitignore` for runtime data exclusion

## [0.6.0] - 2026-04-02

### Added
- **Multi-Team Support**: Restructure agents into teams
  - New `TeamManager` for team isolation and management
  - Agents reorganized into `coding/` and `content/` teams
  - New `teams.yaml` configuration for team definitions
  - CLI commands: `kimi-tachi teams list/switch/info/current`
  - Team-scoped memory support in TachiMemory v3
  - `HybridOrchestrator` supports team-based agent resolution
  - Content team agents based on Three Kingdoms characters
  - Backward compatibility maintained for legacy usage

### Changed
- Agent directory structure: `agents/*.yaml` → `agents/<team>/*.yaml`
- Default coordinator loaded from current team's configuration
- **Project memory directory renamed** from `.memnexus/` to `.mnx/` for brevity
- `TachiMemory.close()` is now async (requires `await`)

### Fixed
- Fixed coroutine warnings in `TachiMemory.close()` method

## [0.5.3] - 2026-04-01

### Added
- **Smart Session Exploration** (主动探查与去重):
  - `SessionExplorer` 类：智能探查历史 session，发现跨会话关联
  - `DecisionDeduplicator`：基于内容指纹的决策去重机制
  - 相关性评分算法：关键词匹配 + 项目关联 + 时间衰减
  - 已探查 Session 追踪：防止重复探查同一 session
  - 增量探查：只处理新增的 session

### Enhanced
- **Memory System v0.5.3**:
  - `recall_on_session_start()` Hook 增强：主动探查其他相关 session
  - Agent 启动时自动发现历史相关决策
  - 决策存储时自动添加指纹标记
  - 新增 `get_exploration_stats()` 查看探查统计

### Technical Details
- New module: `src/kimi_tachi/memory/session_explorer.py`
  - `DecisionFingerprint`: 决策指纹生成与管理
  - `SessionExplorer`: Session 探查与相关性计算
  - Storage: `~/.kimi-tachi/memory/session_explorer/`
- Storage format: JSON (fingerprints + explored sessions)
- Relevance algorithm: keyword overlap (0.3/term) + project match (1.0) + time decay (7-day half-life)

## [0.5.2] - 2026-04-01

### Added
- **kimi-cli 1.28.0+ Compatibility**:
  - Agent Timeout Support: Background tasks now support `timeout` parameter (30-3600s)
    - Updated `BackgroundTaskManager.start_task()` with optional timeout
    - Updated `WireAdapter.send_to_agent()` and `resume_agent()` with agent_timeout
    - Task timeout validation and enforcement
  - Explore Agent Enhancements (nekobasu):
    - Thoroughness Levels: quick/medium/thorough search depth options
    - Git Context Support: Utilize `<git-context>` blocks when provided
    - Updated system prompt with specialist role guidance
  - Hooks Integration Documentation:
    - Added `docs/HOOKS_INTEGRATION.md` with complete integration guide
    - Added `hooks/` directory with example hook scripts:
      - `trace-agent.sh` - Automatic agent call tracing
      - `check-todos.sh` - Todo completion reminder
      - `protect-sensitive.sh` - Sensitive file protection
    - Added `hooks/config.toml.example` for quick setup

### Changed
- Updated `agents/nekobasu.yaml` with thoroughness levels and git context guidance
- Updated `agents/kamaji.yaml` with delegation guide for nekobasu thoroughness levels

### Added (v0.5.2 - Automatic Memory Management)
- **Hooks-Based Automatic Memory** (requires kimi-cli 1.28.0+):
  - `hooks/recall-on-start.sh` - SessionStart hook: Auto-recall context on session start
  - `hooks/store-before-compact.sh` - PreCompact hook: Store key decisions before context compression
  - `hooks/summarize-on-end.sh` - SessionEnd hook: Auto-generate session summary
  - `hooks/process-agent.sh` - PostToolUse hook: Record agent decisions automatically
  - `src/kimi_tachi/hooks/tools.py` - Python tools for hook processing
  - Updated `hooks/config.toml.example` with new automatic memory hooks
  - Updated `docs/HOOKS_INTEGRATION.md` with v0.5.2 features
  - Updated `agents/kamaji.yaml` with automatic memory workflow documentation

### Compatibility
- Requires kimi-cli >=1.25.0 (kimi-cli 1.28.0+ for timeout, thoroughness, and automatic memory features)
- All changes are backward compatible

## [0.5.0] - 2026-03-26

### Added
- **Automatic Memory System**: Persistent code memory powered by MemNexus
  - Project-level memory: Git history, code structure, session context
  - Global memory: Cross-project knowledge sharing
  - Incremental indexing: Only index changed files
  - Seven Samurai memory profiles: Each agent remembers differently
- **Memory CLI Commands**:
  - `kimi-tachi memory init` - Initialize memory for project
  - `kimi-tachi memory index` - Incremental/full indexing
  - `kimi-tachi memory search` - Search project memory
  - `kimi-tachi memory global-search` - Search across projects
  - `kimi-tachi memory recall` - Recall agent context
- **Agent Memory Integration** (automatic, invisible to users):
  - Agents automatically recall context before starting work
  - Agents automatically store key decisions after work
  - Cross-project knowledge lookup for architecture decisions
- **New Module**: `kimi_tachi.memory/` with TachiMemory wrapper
- **New Plugin Tools**: `memory_search`, `memory_recall_agent`, `memory_store_decision`

### Changed
- Updated all Seven Samurai agent YAMLs with memory tool configurations
- Enhanced kamaji.yaml with automatic memory workflow documentation
- Agents now synthesize memory naturally without mentioning "searching memory"

### Dependencies
- Added `memnexus>=0.1.0` as optional dependency for memory features

## [0.4.0] - 2026-03-24

### Added
- **Labor Market Integration**: Register Seven Samurai (七人衆) as built-in subagent types
  - nekobasu, calcifer, shishigami, enma, tasogare, phoenix
  - Use via `Agent(subagent_type="nekobasu", ...)`
- **Agent Session Manager**: Track and resume agent instances across interactions
  - Smart resume suggestions based on activity
  - Cross-session context preservation
- **Background Task Manager**: Async execution for long-running operations
  - Progress tracking and completion callbacks
  - Task cancellation and status queries
- **WireAdapter**: Bridge between Message Bus and kimi-cli Wire system
  - Unified communication interface
  - Transparent local/remote mode switching
- New modules: `session/`, `background/`, `adapters/`

### Changed
- **Breaking**: Require kimi-cli >=1.25.0 (dropped legacy CreateSubagent support)
- Updated `kamaji.yaml` to register subagents as built-in types
- Optimized token usage by ~50% with built-in type system

### Removed
- Legacy `CreateSubagent` and `Task` tool support
- `use_legacy_agents` configuration option

## [0.3.0] - 2026-03-20

### Added
- Skills to Plugins conversion
- Workflow tracing and visualization
- Observability with AgentTracer and WorkflowRenderer
- kimi-cli 1.25.0+ compatibility layer

### Changed
- Moved pytest to dev dependencies
- Updated dependency structure

## [0.2.0] - 2026-03-17

### Added
- Phase 2.1: Dynamic agent creation (MCP 7→2)
- Phase 2.2: Message bus architecture (~500ms → <100ms)
- Phase 2.3: Parallel workflow execution (≥40% parallel)
- Phase 2.4: Context cache optimization (≥80% hit rate)
- Performance metrics collection

## [0.1.0] - 2026-03-17

### Added
- Initial MVP release
- 7 anime character agents (Seven Samurai / 七人衆)
- kamaji orchestrator
- CLI wrapper for kimi-cli
- Basic workflow support
