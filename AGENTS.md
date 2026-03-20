# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI
> 
> *七人の力が一つになれば、どんな敵にも負けない。*

---

## Quick commands

```bash
# Development setup
make install          # Install in editable mode
make install-dev      # Install with dev dependencies

# Development workflow
make format           # Format code with ruff
make lint             # Lint code with ruff
make type-check       # Type check with ty
make test             # Run pytest

# Kimi CLI integration
make setup-kimi       # Install agents to Kimi CLI
make reset-kimi       # Reset and reinstall agents

# Build and release
make build            # Build package
make clean            # Clean build artifacts
```

If using `uv`, run commands with `uv run` prefix:
```bash
uv run make test
uv run kimi-tachi status
```

---

## Project overview

**kimi-tachi** is a multi-agent orchestration layer for Kimi CLI, inspired by anime
characters from Studio Ghibli, Makoto Shinkai, Osamu Tezuka, and Akira Toriyama.

The project provides:
- **7 specialized agents** (七人衆): Each with unique personality and capabilities
- **Agent YAML specifications**: Declarative agent definitions extending Kimi CLI's system
- **Skills system**: Markdown-based skill definitions for reusable capabilities
- **CLI wrapper**: Typer-based CLI for agent management and workflow execution

Unlike monolithic agents, kimi-tachi uses **kamaji (釜爺)** as the sole user interface,
who delegates to other agents behind the scenes via the Task tool.

---

## Tech stack

- **Python**: 3.12+ (configured for 3.12-3.13)
- **CLI framework**: Typer
- **LLM integration**: Native Kimi CLI tools
- **Package management**: uv (recommended) or pip
- **Build**: hatchling
- **Tests**: pytest + pytest-asyncio
- **Lint/Format**: ruff
- **Type checking**: ty (by astral-sh)

---

## Architecture overview

### Agent System (七人衆)

```
┌─────────────────────────────────────────┐
│              用户 (你)                   │
│                  │                      │
│                  ▼                      │
│           ┌───────────┐                 │
│           │  釜爺     │ ◄── 唯一接口     │
│           │ (kamaji)  │                 │
│           └─────┬─────┘                 │
│                 │                       │
│    ┌────────────┼────────────┐          │
│    ▼            ▼            ▼          │
│ ┌──────┐   ┌──────┐   ┌──────┐         │
│ │ 🦌   │   │ 🚌   │   │ 🔥   │         │
│ │山兽神 │   │猫巴士 │   │ 火魔 │  ...    │
│ └──────┘   └──────┘   └──────┘         │
│      幕后工作者 (通过 Task 工具调用)       │
└─────────────────────────────────────────┘
```

**Agent roles:**
| Agent | Role | Origin | Capability |
|-------|------|--------|------------|
| `kamaji` | 釜爺 | Spirited Away | Coordinator - Sole user interface |
| `shishigami` | 山兽神 | Princess Mononoke | Architect - System design |
| `nekobasu` | 猫巴士 | My Neighbor Totoro | Explorer - Fast code exploration |
| `calcifer` | 火魔 | Howl's Moving Castle | Builder - Implementation |
| `enma` | 阎魔王 | Dragon Ball | Reviewer - Code quality |
| `tasogare` | 黄昏 | Your Name | Planner - Planning and research |
| `phoenix` | 火之鸟 | Phoenix (Tezuka) | Librarian - Knowledge management |

### Project structure

```
kimi-tachi/
├── agents/                    # Agent YAML specifications
│   ├── kamaji.yaml           # Coordinator (sole user-facing agent)
│   ├── shishigami.yaml       # Architecture agent
│   ├── nekobasu.yaml         # Exploration agent
│   ├── calcifer.yaml         # Implementation agent
│   ├── enma.yaml             # Review agent
│   ├── tasogare.yaml         # Planning agent
│   └── phoenix.yaml          # Knowledge agent
│
├── skills/                    # Skill definitions (Markdown)
│   ├── kimi-tachi/           # Internal commands
│   ├── todo-enforcer/        # Todo enforcement
│   └── category-router/      # Smart routing
│
├── src/kimi_tachi/           # Python package
│   ├── cli.py                # Typer CLI entry point
│   └── orchestrator/         # Workflow orchestration (optional)
│       ├── __init__.py
│       ├── hybrid_orchestrator.py
│       ├── context_manager.py
│       └── workflow_engine.py
│
├── tests/                    # Test suite
├── docs/                     # Documentation
│   ├── VISION.md             # Design philosophy
│   ├── ROADMAP.md            # Development roadmap
│   ├── STATUS.md             # Current status
│   └── BUG_REPORT_*.md       # Known issues
│
├── pyproject.toml            # Package configuration
├── Makefile                  # Development commands
└── AGENTS.md                 # This file
```

### Key components

#### Agent YAML specs (`agents/*.yaml`)

Agent specifications define:
- **System prompt**: Character personality and behavior rules
- **Tools**: Which tools the agent can use
- **Subagents**: Fixed subagents (for kamaji only)

Example structure:
```yaml
version: 1
agent:
  name: "kamaji"
  extend: default
  system_prompt_args:
    ROLE: "Boiler Room Chief"
    ROLE_ADDITIONAL: |
      # Character definition and rules...
  tools:
    - "kimi_cli.tools.shell:Shell"
    - "kimi_cli.tools.file:ReadFile"
    # ... more tools
  subagents:
    shishigami:
      path: ./shishigami.yaml
      description: "🦌 Forest Deity - Architecture"
```

**Important**: Due to MCP server duplication issues (see
[BUG_REPORT_MCP_DUPLICATION.md](BUG_REPORT_MCP_DUPLICATION.md)), subagents should
minimize MCP dependencies. Consider using `CreateSubagent` for MCP-requiring tasks.

#### CLI (`src/kimi_tachi/cli.py`)

The CLI provides:
- `kimi-tachi install`: Install agents to `~/.kimi/agents/kimi-tachi/`
- `kimi-tachi run`: Run Kimi CLI with specified agent
- `kimi-tachi workflow`: Execute multi-agent workflows
- `kimi-tachi status`: Check installation status

#### Skills (`skills/*/`)

Skills are reusable capabilities defined in Markdown:
- `SKILL.md`: Skill definition with triggers and instructions
- Loaded by Kimi CLI when triggers match

---

## Development workflow

### Setup

```bash
# Clone and setup
git clone <repo-url>
cd kimi-tachi

# Install in development mode
make install-dev
# or: pip install -e ".[dev]"

# Install agents to Kimi CLI
make setup-kimi
```

### Making changes

#### Modifying agent behavior

1. Edit `agents/<agent>.yaml`:
   - Update `system_prompt_args` for behavior changes
   - Modify `tools` list to change available tools

2. Reinstall to Kimi CLI:
   ```bash
   kimi-tachi install --force
   ```

3. Test:
   ```bash
   kimi-tachi run --agent <agent-name>
   ```

#### Modifying CLI code

1. Edit `src/kimi_tachi/cli.py` or other Python files

2. If using editable install (`pip install -e .`), changes are immediate

3. Test:
   ```bash
   kimi-tachi --help
   ```

#### Adding a new skill

1. Create `skills/<skill-name>/SKILL.md`:
   ```markdown
   ---
   name: <skill-name>
   description: <description>
   triggers:
     - "/<command>"
   ---
   
   # Skill content...
   ```

2. Reinstall:
   ```bash
   kimi-tachi install --force
   ```

### Testing

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_specific.py -v

# Type checking
make type-check
```

---

## Conventions and quality

### Python code

- **Python version**: 3.12+ (specified in `pyproject.toml` and `.python-version`)
- **Line length**: 100 characters
- **Import style**: Use `from __future__ import annotations`
- **Type hints**: Encouraged, checked by ty

### Ruff rules

Enabled rules: `E`, `F`, `UP`, `B`, `SIM`, `I`

```bash
make format    # Auto-format code
make lint      # Check linting
```

### Agent YAML conventions

1. **Naming**: Use lowercase with underscores (e.g., `shishigami`, `nekobasu`)
2. **Descriptions**: Keep under 100 characters, include emoji
3. **System prompts**: 
   - Maintain character personality
   - Include clear role definition
   - Document tool usage patterns
4. **Tools**: Only include tools the agent actually needs

---

## Git commit messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <subject>
```

### Allowed types

| Type | Use for |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `test` | Adding or fixing tests |
| `refactor` | Code refactoring |
| `chore` | Maintenance tasks |
| `style` | Code style changes (formatting) |
| `docs` | Documentation changes |
| `perf` | Performance improvements |
| `build` | Build system changes |
| `ci` | CI/CD changes |
| `revert` | Reverting changes |

### Scopes

Common scopes for kimi-tachi:
- `agent/<name>`: Agent changes (e.g., `agent/kamaji`, `agent/calcifer`)
- `skill/<name>`: Skill changes
- `cli`: CLI commands
- `orchestrator`: Workflow orchestration
- `docs`: Documentation

### Examples

```
feat(agent/kamaji): add auto-orchestration for complex tasks

fix(agent/nekobasu): correct file pattern matching in explore mode

docs: update ROADMAP with Phase 2 details

test: add unit tests for workflow engine

refactor(cli): extract common agent loading logic
```

---

## Versioning

kimi-tachi follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`):

- **MAJOR**: Breaking changes (e.g., agent API changes)
- **MINOR**: New features, improvements, non-breaking changes
- **PATCH**: Bug fixes, documentation updates

Examples: `0.1.0` → `0.2.0` → `0.2.1`

### Version bump guidelines

| Change type | Version bump |
|-------------|--------------|
| New agent added | MINOR |
| Agent behavior change | MINOR |
| New skill | MINOR |
| CLI command added | MINOR |
| Bug fix | PATCH |
| Documentation update | PATCH |
| Breaking API change | MAJOR |

---

## Release workflow

### Preparation

1. Ensure `main` branch is up to date:
   ```bash
   git checkout main
   git pull origin main
   ```

2. Run full test suite:
   ```bash
   make check
   make test
   ```

3. Update documentation:
   - Update `CHANGELOG.md`
   - Update `STATUS.md` if needed
   - Verify `ROADMAP.md` reflects current state

### Version bump

1. Create release branch:
   ```bash
   git checkout -b bump-0.2.0
   ```

2. Update version in:
   - `pyproject.toml`: `version = "0.2.0"`
   - `src/kimi_tachi/__init__.py`: `__version__ = "0.2.0"`

3. Commit changes:
   ```bash
   git add -A
   git commit -m "chore(release): bump version to 0.2.0"
   ```

4. Push and create PR:
   ```bash
   git push origin bump-0.2.0
   # Create PR on GitHub
   ```

### Release

1. Merge PR to `main`

2. Pull latest:
   ```bash
   git checkout main
   git pull origin main
   ```

3. Create and push tag:
   ```bash
   git tag 0.2.0
   git push origin 0.2.0
   ```

4. GitHub Actions will handle:
   - Building package
   - Creating GitHub Release
   - Publishing to PyPI (if configured)

### Post-release

1. Install and verify:
   ```bash
   pip install kimi-tachi==0.2.0
   kimi-tachi --version
   kimi-tachi status
   ```

2. Update development environment:
   ```bash
   pip install -e ".[dev]"
   ```

---

## Agent development guidelines

### Creating a new agent

1. **Copy template** from existing agent:
   ```bash
   cp agents/calcifer.yaml agents/my_agent.yaml
   ```

2. **Define character**:
   - Choose an anime character with clear personality
   - Define role that maps to a software engineering task
   - Write system prompt that captures the character's voice

3. **Select tools**:
   - Start minimal (Shell, ReadFile, WriteFile, StrReplaceFile)
   - Add specialized tools as needed
   - Avoid MCP tools in subagents (see MCP issue)

4. **Test iteratively**:
   ```bash
   kimi-tachi install --force
   kimi-tachi run --agent my_agent
   ```

### Agent testing checklist

Before committing agent changes:

- [ ] Agent loads without YAML syntax errors
- [ ] System prompt renders correctly
- [ ] All specified tools are available
- [ ] Character personality is consistent
- [ ] Agent responds appropriately to role-specific tasks

### MCP considerations

**Important**: Due to kimi-cli's current behavior, each fixed subagent loads
its own MCP servers, causing resource duplication.

**Mitigation strategies**:
1. Minimize MCP dependencies in subagent YAMLs
2. Use `CreateSubagent` for MCP-requiring tasks
3. Document MCP usage limitations

See [BUG_REPORT_MCP_DUPLICATION.md](BUG_REPORT_MCP_DUPLICATION.md) for details.

---

## Resources

- [VISION.md](VISION.md): Project vision and design philosophy
- [ROADMAP.md](ROADMAP.md): Development roadmap
- [STATUS.md](STATUS.md): Current project status
- [README.md](README.md): User-facing documentation

### External references

- [Kimi CLI Documentation](https://github.com/your-org/kimi-cli)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

---

*「さあ、働け！働け！」- Kamaji*
