# Contributing to Inspectra

Thank you for your interest in contributing!

---

## Getting Started

### 1. Fork and clone

```bash
git clone https://github.com/iamakashsoni/inspectra.git
cd inspectra
```

### 2. Set up the dev environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Verify setup

```bash
pytest          # all tests should pass
ruff check .    # no lint errors
```

---

## Project Structure

```
src/inspectra/
├── cli.py              # CLI entry point (Typer)
├── config/             # Settings and YAML loader
├── git/                # Diff parsing and file filtering
├── llm/                # LLM provider abstraction + implementations
├── review/             # Engine, prompts, severity, formatter
├── github/             # GitHub API integration
├── output/             # Console, Markdown, SARIF
└── utils/              # Logger, tokenizer, chunker, cache

tests/                  # One test file per module
```

---

## Making Changes

### Adding a new LLM provider

1. Create `src/inspectra/llm/your_provider.py` extending `BaseLLMProvider`
2. Add the provider to `LLMProvider` enum in `config/settings.py`
3. Register it in `llm/provider_factory.py`
4. Add tests in `tests/test_your_provider.py`

### Adding a new output format

1. Create `src/inspectra/output/your_format.py`
2. Export from `output/__init__.py`
3. Add `--your-format` flag in `cli.py`

---

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_reviewer.py

# With coverage report
pytest --cov=inspectra --cov-report=html
open htmlcov/index.html

# Fast (no coverage)
pytest -p no:cov
```

---

## Code Style

This project uses `ruff` for linting and formatting.

```bash
# Check
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format
ruff format src/ tests/
```

Lines are 100 characters wide. Type hints are required on all public functions.

---

## Pull Request Process

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes with tests
3. Ensure `pytest` and `ruff check` both pass
4. Update `CHANGELOG.md` under `[Unreleased]`
5. Open a PR with a clear description of what and why

---

## Reporting Issues

Use GitHub Issues. Please include:
- Your OS and Python version
- The command you ran
- The full error output
- Your `.inspectra.yml` (redact any secrets)
