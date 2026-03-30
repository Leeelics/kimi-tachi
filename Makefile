# Kimi-Tachi Makefile
# Inspired by kimi-cli's CI/CD practices

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available make targets.
	@echo "Available make targets:"
	@awk 'BEGIN { FS = ":.*## " } /^[A-Za-z0-9_.-]+:.*## / { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ========== Setup ==========

.PHONY: prepare
prepare: ## Install dependencies and setup environment.
	@echo "==> Syncing dependencies"
	@uv sync --all-extras
	@echo "==> Installing package in editable mode"
	@uv pip install -e ".[dev]"

.PHONY: install-hooks
install-hooks: ## Install pre-commit hooks (if pre-commit is available).
	@if command -v pre-commit >/dev/null 2>&1; then \
		echo "==> Installing pre-commit hooks"; \
		pre-commit install; \
	else \
		echo "⚠️  pre-commit not found. Install with: uv pip install pre-commit"; \
	fi

# ========== Development ==========

.PHONY: format
format: ## Auto-format code with ruff.
	@echo "==> Formatting code with ruff"
	@uv run ruff check --fix
	@uv run ruff format

.PHONY: check
check: ## Run linting and format checks.
	@echo "==> Running ruff check"
	@uv run ruff check
	@echo "==> Running ruff format check"
	@uv run ruff format --check

.PHONY: test
test: ## Run all tests.
	@echo "==> Running tests"
	@uv run pytest tests/ -v --tb=short

.PHONY: test-cov
test-cov: ## Run tests with coverage.
	@echo "==> Running tests with coverage"
	@uv run pytest tests/ -v --tb=short --cov=kimi_tachi --cov-report=term-missing

.PHONY: test-memory
test-memory: ## Run memory-specific tests.
	@echo "==> Running memory tests"
	@uv run pytest tests/test_memory.py -v --tb=short

# ========== Build & Release ==========

.PHONY: version-check
version-check: ## Check version consistency across files.
	@echo "==> Checking version consistency"
	@python3 scripts/check_version.py

.PHONY: build
build: ## Build package distribution.
	@echo "==> Building package"
	@uv build

.PHONY: build-check
build-check: build ## Build and verify package can be installed.
	@echo "==> Testing package installation"
	@python3 scripts/test_build.py

.PHONY: clean
clean: ## Clean build artifacts.
	@echo "==> Cleaning build artifacts"
	@rm -rf dist/ build/ *.egg-info
	@rm -rf .pytest_cache .ruff_cache
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ========== CI/CD Helpers ==========

.PHONY: ci-check
ci-check: check version-check test ## Run all CI checks (lint + version + test).
	@echo "✅ All CI checks passed"

.PHONY: ci-build
ci-build: clean build-check ## Run CI build process.
	@echo "✅ CI build completed"

# ========== Documentation ==========

.PHONY: docs-serve
docs-serve: ## Serve documentation locally (if docs exist).
	@if [ -f mkdocs.yml ]; then \
		echo "==> Serving documentation"; \
		uv run mkdocs serve; \
	else \
		echo "⚠️  mkdocs.yml not found"; \
	fi

.PHONY: changelog-check
changelog-check: ## Check if CHANGELOG.md has entry for current version.
	@python3 scripts/check_version.py

# ========== Utility ==========

.PHONY: update-deps
update-deps: ## Update dependencies.
	@echo "==> Updating dependencies"
	@uv lock --upgrade

.PHONY: shell
shell: ## Start a shell with the virtual environment activated.
	@uv shell

.PHONY: info
info: ## Show project information.
	@echo "Project: kimi-tachi"
	@echo "Version: $$(uv run python -c 'import kimi_tachi; print(kimi_tachi.__version__)')"
	@echo "Python:  $$(uv run python --version)"
	@echo "UV:      $$(uv --version)"
