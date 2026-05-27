.PHONY: install dev test lint typecheck format check build clean help

# ── Setup ──────────────────────────────────────────────────────────────────────

install:  ## Install package (production deps only)
	pip install -e .

dev:  ## Install package with all dev dependencies
	pip install -e ".[dev]"

# ── Quality ────────────────────────────────────────────────────────────────────

test:  ## Run test suite with coverage
	pytest --cov=inspectra --cov-report=term-missing

test-fast:  ## Run tests without coverage (faster)
	pytest -q --no-cov

test-verbose:  ## Run tests with full output
	pytest -v

lint:  ## Lint with ruff
	ruff check src/ tests/

lint-fix:  ## Auto-fix lint issues
	ruff check --fix src/ tests/

format:  ## Format code with ruff
	ruff format src/ tests/

format-check:  ## Check formatting without changing files
	ruff format --check src/ tests/

typecheck:  ## Run mypy type checker
	mypy src/

check: lint format-check typecheck test  ## Run all checks (lint + format + types + tests)

# ── Build ──────────────────────────────────────────────────────────────────────

build: clean  ## Build wheel and source distribution
	python -m build
	twine check dist/*

clean:  ## Remove build artefacts
	rm -rf dist/ build/ src/*.egg-info/ .eggs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# ── Publish ────────────────────────────────────────────────────────────────────

publish-test: build  ## Publish to TestPyPI
	twine upload --repository testpypi dist/*

publish: build  ## Publish to PyPI (production)
	twine upload dist/*

# ── Local review ──────────────────────────────────────────────────────────────

review:  ## Run Inspectra on current git diff (dry run)
	inspectra review --dry-run --no-pr-summary

review-live:  ## Run Inspectra with Ollama (requires Ollama running)
	inspectra review --provider ollama --no-pr-summary

# ── Cache ──────────────────────────────────────────────────────────────────────

cache-clear:  ## Clear the Inspectra LLM response cache
	inspectra cache-clear

# ── Help ──────────────────────────────────────────────────────────────────────

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
