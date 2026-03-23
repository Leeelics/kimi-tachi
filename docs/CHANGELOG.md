# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Dynamic Agent Creation**: On-demand subagent creation with AgentFactory
- **Message Bus Architecture**: Async message bus for inter-agent communication
  - Point-to-point messaging
  - Broadcast and multicast
  - Publish-subscribe pattern
  - SQLite persistence for reliability
  - Distributed tracing support
- **Performance Metrics Collection**: Latency, throughput, and parallel execution tracking
- Comprehensive project documentation (AGENTS.md, ROADMAP.md)
- Type checking with `ty` (replaced pyright)
- Code quality enforcement with ruff

### Changed
- **MCP Process Reduction**: Reduced from 7 fixed processes to ≤2 dynamic processes
- Migrated default branch from `master` to `main`
- Cleaned up project structure (removed unrelated code in src/)

### Fixed
- Deadlock in MessageStore cleanup operation
- Code style issues (trailing whitespace, ambiguous variable names, etc.)
- Import organization and unused imports
- Makefile formatting

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
