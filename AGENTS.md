# Kimi-Tachi

## Quick commands

```bash
make prepare   # install deps and git hooks
make format    # auto-format with ruff
make check     # ruff lint + format check
make test      # run all tests
make test-cov  # run tests with coverage
make build     # build package
```

Use `uv run ...` for one-off commands.

## Project overview

**kimi-tachi** is a multi-agent task orchestration layer for Kimi CLI. It provides themed teams of specialized agents (coordinators, explorers, builders, reviewers, planners, librarians) that work together behind the scenes.

## Tech stack

- Python 3.12+
- CLI framework: Typer
- Package management: uv
- Tests: pytest + pytest-asyncio
- Lint/format: ruff

## Repo map

- `src/kimi_tachi/cli.py` — CLI entry (install, uninstall, teams, status)
- `src/kimi_tachi/team/` — Team management (`TeamManager`, `teams.yaml` parsing)
- `src/kimi_tachi/compatibility.py` — kimi-cli version compatibility checks
- `src/kimi_tachi/memory/` — Optional MemNexus-based code memory (TachiMemory, agent profiles)
- `agents/` — Agent YAML specs and team definitions
- `plugins/` — CLI plugins for kimi-cli 1.25.0+
- `skills/` — Documentation and guidance skills
- `scripts/evaluate_cleanup.py` — Health and efficiency evaluation harness
- `BENCHMARK.md` — Efficiency baseline and capability map
- `docs/hooks.md` — Native hooks migration guide
- `tests/unit/` — Unit tests (mocked, no subprocess)
- `tests/integration/` — Integration tests (subprocess, external systems)
- `tests_e2e/` — End-to-end CLI tests

## Conventions and quality

- Python >= 3.12; line length 100.
- Ruff handles lint + format.
- Tests use pytest + pytest-asyncio; files are `tests_*/test_*.py`.
- CLI entry: `kimi-tachi` -> `src/kimi_tachi/cli.py:main()`.

## Git commit messages

Conventional Commits format:

```
<type>(<scope>): <subject>
```

Allowed types:
`feat`, `fix`, `test`, `refactor`, `chore`, `style`, `docs`, `perf`, `build`, `ci`, `revert`.

## Versioning and release

Follows Semantic Versioning (`MAJOR.MINOR.PATCH`).

### Release checklist

1. Ensure `main` is up to date.
2. Update `CHANGELOG.md` with a new section for the version.
3. Bump version in:
   - `pyproject.toml`
   - `src/kimi_tachi/__init__.py`
   - `plugins/kimi-tachi/plugin.json`
   - `tests/unit/test_placeholder.py` (version assertion)
4. Run `uv sync` to align `uv.lock`.
5. Commit with message: `chore(release): bump version to X.Y.Z`.
6. Push to `main`.
7. Tag with `vX.Y.Z` and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
8. GitHub Actions will create the GitHub Release and publish to PyPI.

## Notes

- Tag **must** use `v` prefix (e.g. `v0.6.2`) to trigger the Release workflow.
- `make check` and `make test` must pass before pushing.
