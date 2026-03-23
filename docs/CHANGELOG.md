# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.2.0] - 2026-03-23

### Phase 2: Architecture Optimization

#### Phase 2.1 - Dynamic Agent Creation
- **AgentFactory**: On-demand subagent creation without MCP overhead
- **Dual-mode operation**: Dynamic (default) or Fixed (legacy)
- **MCP Process Reduction**: Reduced from 7 fixed processes to ≤2 dynamic processes
- Environment variable `KIMI_TACHI_DYNAMIC_AGENTS` for mode control

#### Phase 2.2 - Message Bus Architecture
- **MessageBus**: Async message passing between agents
- **Communication patterns**: Point-to-point, broadcast, multicast, publish-subscribe
- **Message models**: Pydantic-based with priority, TTL, delivery status
- **Persistence**: SQLite storage for message reliability
- **Tracing**: Distributed tracing with span context
- Environment variable `KIMI_TACHI_MESSAGE_BUS_ENABLED` for control

#### Phase 2.3 - Parallel Workflow Execution
- **TaskDependencyAnalyzer**: Automatic dependency detection
  - Semantic analysis (planning → implementation → review)
  - File-based dependency detection
  - Explicit dependency support
- **ParallelScheduler**: Parallel phase execution with resource limits
- **WorkflowEngine**: Enhanced with parallel execution support
- **Execution plan**: Automatic batch generation based on dependencies

#### Phase 2.4 - Context Cache Optimization
- **FileContentCache**: Two-tier caching (memory + disk)
  - LRU eviction policy
  - Automatic file modification detection
  - Hash-based cache invalidation
- **SemanticIndex**: AST-based code indexing
  - Tree-sitter powered parsing
  - Fast symbol lookup (<100ms)
  - Incremental index updates
- **AnalysisResultCache**: LLM result caching with TTL
- **ContextCompressor**: Token usage reduction (30%+)
  - Python-specific compression
  - Markdown/config file compression
  - Conversation history compression
- Environment variable `KIMI_TACHI_ENABLE_CACHE` for control

#### Performance Metrics
- MCP processes: 7 → ≤2 (71% reduction)
- Message latency: ~500ms → <100ms (80% reduction)
- Parallel execution: 0% → ≥40% (new)
- Cache hit rate: 0% → ≥80% (new)
- Token usage: 100% → ~70% (30% reduction)

### Added
- **Performance Metrics Collection**: Latency, throughput, parallel execution tracking
- **tree-sitter integration**: Python AST parsing for semantic index
- Comprehensive test coverage: 59 tests for Phase 2 features
- Project documentation: Phase 2 design documents

### Changed
- Updated README with v0.2.0 features and architecture
- Enhanced HybridOrchestrator with cache integration
- Improved WorkflowEngine with parallel execution

### Fixed
- Deadlock in MessageStore cleanup operation
- Circular imports in workflow orchestrator
- SQLite keyword conflicts in semantic index
- Code style issues (trailing whitespace, etc.)

## [0.1.0] - 2026-03-20

### Added
- Initial release of kimi-tachi
- 7 anime character agents (七人衆):
  - kamaji (釜爺) - Coordinator
  - shishigami (山兽神) - Architect
  - nekobasu (猫巴士) - Explorer
  - calcifer (火魔) - Builder
  - enma (阎魔王) - Reviewer
  - tasogare (黄昏) - Planner
  - phoenix (火之鸟) - Librarian
- CLI wrapper with Typer
- Agent YAML specifications for all 7 characters
- Initial skills: todo-enforcer, category-router, kimi-tachi
- Workflow orchestration framework
- Context manager for session persistence
