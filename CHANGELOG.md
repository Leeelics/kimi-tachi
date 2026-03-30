# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
