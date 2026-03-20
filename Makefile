.PHONY: install dev test format lint clean

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Development
dev: install-dev
	@echo "kimi-tachi development environment ready"
	@echo "Run 'kimi-tachi install' to install agents to Kimi CLI"

# Testing
test:
	pytest tests/ -v

# Code quality
format:
	ruff format src/ tests/

lint:
	ruff check src/ tests/

type-check:
	ty check src/

# Installation to Kimi CLI
setup-kimi:
	kimi-tachi install

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build: clean
	python -m build

# Release (requires proper credentials)
publish: build
	python -m twine upload dist/*
