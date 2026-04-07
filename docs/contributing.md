# Contributing to kimi-tachi

Thank you for your interest in contributing to **kimi-tachi (君たち)**! 

This document provides guidelines for contributing to the project.

## 🎯 Project Philosophy

Before contributing, please understand our core principles:

1. **Native First**: Use Kimi CLI's native capabilities when possible
2. **Zero Intrusion**: Don't modify Kimi CLI source code
3. **Engineering Reliability**: Focus on correctness over quantity
4. **Many Kimis, One Goal**: Agents work together seamlessly

## 🚀 Quick Start

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd kimi-tachi

# Install in development mode
make dev

# Or manually:
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Test CLI
kimi-tachi --help

# Check status
kimi-tachi status

# Install agents to Kimi CLI
kimi-tachi install
```

## 📁 Repository Structure

```
kimi-tachi/
├── agents/              # Agent YAML configurations
│   ├── teams.yaml       # Team definitions
│   ├── coding/          # Coding team (Seven Samurai)
│   └── content/         # Content team
├── skills/              # Skill definitions (Markdown)
├── src/kimi_tachi/      # Python source code
│   ├── team/            # Team management
│   ├── memory/          # Memory system
│   └── ...
├── tests/               # Test files
└── docs/                # Documentation
```

## 🤝 How to Contribute

### Contributing an Agent

Agents are YAML configurations that define specialized AI assistants.

#### Agent Naming

- Use anime character names in romanized form (e.g., `kamaji`, `calcifer`)
- Should reflect the agent's role and personality
- Check existing agents for inspiration
- See [roadmap.md](./roadmap.md) for the character system design

#### Agent Structure

```yaml
version: 1
agent:
  name: "your-agent"
  extend: ./kamaji.yaml  # or default
  system_prompt_args:
    ROLE: "Role Name"
    ROLE_ADDITIONAL: |
      # Detailed role description
      # Include:
      # - Domain expertise
      # - Approach/methodology
      # - Output format
      # - When to escalate
  
  # Tools this agent can use
  tools:
    - "kimi_cli.tools.shell:Shell"
    - ...
  
  # Subagents this agent can delegate to
  subagents:
    other-agent:
      path: ./other-agent.yaml
      description: "When to use this subagent"
```

#### Agent Guidelines

1. **Clear Role Definition**: What is this agent's specialty?
2. **Specific Instructions**: How should it approach tasks?
3. **Output Format**: What format should responses follow?
4. **Escalation Rules**: When should it ask for help?

#### Testing Your Agent

```bash
# Install your agent
kimi-tachi install

# Test it
kimi --agent ~/.kimi/agents/kimi-tachi/your-agent.yaml
```

### Contributing a Team

Teams are groups of agents organized by domain.

#### Team Structure

```yaml
# agents/teams.yaml
teams:
  your-team:
    name: "Your Team Name"
    description: "What this team specializes in"
    coordinator: "agent-name"  # Default agent when team is active
    theme: "default"
    icon: "🎭"
    agents_dir: "your-team"    # Directory containing agent YAMLs
    memory_namespace: "your-team"
    agents:
      agent-name:
        name: "Agent Display Name"
        role: "coordinator|worker|specialist"
        description: "What this agent does"
        icon: "🤖"
```

#### Team Directory

```
agents/
├── teams.yaml
└── your-team/
    ├── coordinator.yaml    # Team coordinator
    ├── worker1.yaml        # Team members
    └── worker2.yaml
```

#### Adding Agents to a Team

1. Create agent YAML files in the team's directory
2. Register agents in `teams.yaml` under the team's `agents` section
3. Ensure the coordinator agent has `role: coordinator`

#### Testing Your Team

```bash
# List all teams
kimi-tachi teams list

# Switch to your team
kimi-tachi teams switch your-team

# Start with team's coordinator
kimi-tachi start

# Or use specific agent from the team
kimi-tachi run -a agent-name
```

---

### Contributing a Skill

Skills are Markdown files that provide reusable capabilities.

#### Skill Structure

```markdown
---
name: skill-name
description: Brief description of what this skill does
---

# Skill Name

## Overview

What this skill does and when to use it.

## Usage

### Pattern 1
Description of pattern 1.

### Pattern 2
Description of pattern 2.

## Examples

### Example 1
```
Input: ...
Output: ...
```

## Best Practices

- Tip 1
- Tip 2
```

#### Skill Guidelines

1. **Clear Purpose**: One skill should do one thing well
2. **Actionable**: Provide concrete patterns and examples
3. **Testable**: Include example inputs/outputs
4. **Consistent**: Follow existing skill formats

#### Skill Location

```
skills/
└── your-skill/
    └── SKILL.md
```

### Contributing Code

#### Python Code Style

We use:
- **Ruff** for linting and formatting
- **Pyright** for type checking
- **Pytest** for testing

```bash
# Format code
make format

# Run linter
make lint

# Type check
make type-check

# Run tests
make test
```

#### Code Guidelines

1. **Type Hints**: Use type annotations
2. **Docstrings**: Document functions and classes
3. **Tests**: Add tests for new functionality
4. **Minimal Changes**: Make the smallest change necessary

## 📋 Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** your changes
5. **Commit** with clear messages (`git commit -m 'Add amazing feature'`)
6. **Push** to your fork (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass (`make test`)
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] PR description explains the changes

### PR Title Format

We follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): subject

Examples:
- feat(agent): Add shishigami for architecture design
- feat(skill): Add debug-helper for troubleshooting
- docs: Update installation guide
- fix(agent/kamaji): Correct typo in system prompt
```

Allowed types: `feat`, `fix`, `test`, `refactor`, `chore`, `style`, `docs`, `perf`, `build`, `ci`, `revert`

Common scopes: `agent/<name>`, `skill/<name>`, `cli`, `orchestrator`, `docs`

## 🔄 Continuous Integration

We use GitHub Actions for CI/CD. All PRs must pass the following checks:

### Automated Checks

| Check | Tool | Description |
|-------|------|-------------|
| **Code Quality** | ruff | Format and lint checking |
| **Type Check** | ty | Static type analysis |
| **Tests** | pytest | Unit and integration tests |
| **Agent Validation** | pyyaml | YAML syntax and consistency |
| **Documentation** | - | README and docs completeness |
| **Build** | build | Package build verification |

### Before Submitting PR

Ensure all checks pass locally:

```bash
# Run all quality checks
make lint
make type-check
make test

# Validate agents
python -c "import yaml; [yaml.safe_load(open(f)) for f in __import__('glob').glob('agents/*.yaml')]"
```

### CI Configuration

CI workflows are defined in `.github/workflows/`:
- `ci.yml` - Runs on every push and PR
- `release.yml` - Runs on version tags for PyPI release

See [GITHUB_SETUP.md](./GITHUB_SETUP.md) for detailed CI/CD setup instructions.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_agents.py -v

# Run with coverage
pytest --cov=src/kimi_tachi tests/
```

### Writing Tests

```python
# tests/test_your_feature.py
def test_your_feature():
    """Test description."""
    result = your_function()
    assert result == expected_value
```

## 📝 Documentation

### Updating Documentation

- **README.md**: Project overview, installation, basic usage
- **VISION.md**: Project philosophy, roadmap
- **QUICKSTART.md**: 5-minute getting started guide
- **STATUS.md**: Current project status

### Documentation Style

- Use clear, concise language
- Include code examples
- Keep examples runnable
- Update when features change

## 🐛 Reporting Issues

### Bug Reports

Include:
1. **Description**: What happened?
2. **Steps to Reproduce**: How can we reproduce it?
3. **Expected Behavior**: What should have happened?
4. **Environment**: OS, Python version, Kimi CLI version
5. **Logs**: Relevant error messages

### Feature Requests

Include:
1. **Use Case**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: What else did you consider?

## 💬 Community

### Communication Channels

- GitHub Issues: Bug reports, feature requests
- GitHub Discussions: General questions, ideas
- Pull Requests: Code review, implementation

### Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on the issue, not the person
- Assume good intentions

## 🎓 Learning Resources

### Understanding kimi-tachi

1. Read [VISION.md](./VISION.md) for project philosophy
2. Read [README.md](../README.md) for technical details
3. Study existing agents in `agents/`
4. Study existing skills in `skills/`

### Understanding Kimi CLI

- [Kimi CLI Documentation](https://github.com/moonshot-ai/Kimi-CLI)
- Agent YAML format
- Skill system
- Available tools

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in relevant documentation

---

## Questions?

If you have questions:
1. Check existing documentation
2. Search closed issues
3. Open a new discussion

**Thank you for contributing to kimi-tachi!**

*Many Kimis, One Goal.*
