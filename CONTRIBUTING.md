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

---

## Phase 2: Adding new analyzers

1. Subclass `BaseAnalyzer` in `src/inspectra/review/analyzers/`
2. Set `name` and `supported_languages` as class attributes
3. Implement `analyze(file_path, full_content, diff_text) -> list[AnalyzerFinding]`
4. Register in `build_default_registry()` (in `registry.py`)

```python
from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    name = "my-analyzer"
    supported_languages = ["python"]

    def analyze(self, file_path, full_content, diff_text):
        return [AnalyzerFinding(
            rule_id="MINE/R001",
            severity="medium",
            category="Bugs",
            title="My custom finding",
            explanation="...",
            file_path=file_path,
            line_number=42,
            analyzer_name=self.name,
        )]
```

## Phase 2: Adding new LLM providers

For OpenAI-compatible providers (Together, Groq, Anyscale, etc.):

```python
from inspectra.llm.openai_compatible import OpenAICompatibleProvider

class TogetherProvider(OpenAICompatibleProvider):
    def __init__(self, *, api_key, model="meta-llama/Llama-3-70b-chat-hf", **kwargs):
        super().__init__(
            api_key=api_key, model=model,
            base_url="https://api.together.xyz/v1",
            **kwargs,
        )
```

Then add the provider to the `LLMProvider` enum in `config/settings.py` and a branch in `llm/provider_factory.py`.
