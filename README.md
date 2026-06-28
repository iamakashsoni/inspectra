<div align="center">

# 🔍 Inspectra

**Self-hosted AI code reviewer for pull requests.**

Reviews git diffs with LLMs · Posts actionable feedback on your GitHub PR · Works with 5 providers

[![CI](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml/badge.svg)](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/inspectra.svg)](https://pypi.org/project/inspectra/)
[![Python](https://img.shields.io/pypi/pyversions/inspectra.svg)](https://pypi.org/project/inspectra/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/iamakashsoni/inspectra/pulls)

</div>

---

> **It reviews your code** — bugs, security vulnerabilities, performance issues, architectural concerns.
> **It does not just find syntax errors** — it understands the surrounding code, the PR intent, and cross-file dependencies to give precise, actionable suggestions.

---

## Table of Contents

- [Quick Start](#quick-start)
- [LLM Providers](#llm-providers)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [GitHub Actions](#github-actions)
- [Features](#features)
- [Architecture](#architecture)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)
- [Author](#author)

---

## Quick Start

### Install

```bash
pip install inspectra
```

### Review your local changes

```bash
# Free cloud (Nvidia NIM — get a key at build.nvidia.com)
export NVIDIA_API_KEY=nvapi-...
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct

# Or fully local (Ollama — free, private)
ollama pull qwen2.5-coder:14b
inspectra review
```

### Review a GitHub PR

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=myorg/myrepo

inspectra review --provider nvidia --pr 42 --post-comment
```

---

## LLM Providers

Five providers, one interface. Switch with `--provider`, no code changes.

| Provider | Default model | Free | Private | Setup |
|----------|---------------|:----:|:-------:|-------|
| `ollama` | `qwen2.5-coder:14b` | ✅ | ✅ | Local install |
| `nvidia` | `meta/llama-3.3-70b-instruct` | ✅ | ✅* | Free API key |
| `openai` | `gpt-4o-mini` | ❌ | ❌ | Paid API key |
| `anthropic` | `claude-sonnet-4-20250514` | ❌ | ❌ | Paid API key |
| `openrouter` | `anthropic/claude-3.5-sonnet` | ❌ | ❌ | Paid API key |

\* Nvidia cloud is private to your account; self-hosted NIM is fully air-gapped.

**➜ Full provider setup guide:** [docs/llm-providers.md](docs/llm-providers.md)

---

## CLI Reference

```
Commands:
  review          Review the current git diff or a GitHub PR
  init            Create a default .inspectra.yml
  models          List available Ollama models
  cache-clear     Clear the local LLM response cache
  suppress        Add a false-positive suppression to the baseline
  baseline-show   Show all suppressions in the baseline file
  version         Show version

review options:
  -p, --provider          ollama | openai | anthropic | nvidia | openrouter  [default: ollama]
  -m, --model             Model name (provider-specific)
      --base-url          Override provider API URL (self-hosted NIM, on-prem proxy)
  -c, --config            Path to .inspectra.yml
  -o, --output            Write Markdown report to file
      --sarif             Write SARIF report (GitHub Code Scanning)
      --pr                GitHub PR number
      --post-comment      Post review as a GitHub PR comment
      --inline/--no-inline  Post inline comments at issue lines  [default: on]
      --pr-summary/--no-pr-summary  Generate AI PR-level summary  [default: on]
      --staged            Review staged changes only
      --cache             Cache LLM responses to .inspectra_cache/
      --concurrency       Max concurrent LLM calls (0 = auto)
      --baseline          Path to .inspectra-baseline.json for false-positive suppression
      --pr-intent         PR description (auto-extracted from PR if --pr is set)
      --no-file-context   Disable full file content in prompt
      --no-analyzers      Disable deterministic analyzers (Bandit/Semgrep/regex)
      --no-cross-file     Disable cross-file consistency review
      --no-language-rules Disable language-specific antipattern hints
      --dry-run           Parse diff without calling the LLM
      --fail-on-high      Exit 1 when critical/high issues found  [default: on]
  -v, --verbose           Enable verbose logging
```

---

## Configuration

Create `.inspectra.yml` (or run `inspectra init`):

```yaml
provider: nvidia
model: meta/llama-3.3-70b-instruct

ollama:
  host: http://localhost:11434
  timeout: 300

review:
  security: true
  bugs: true
  performance: true
  maintainability: true
  architecture: true

exclude:
  - "*.lock"
  - "dist/*"
  - "vendor/*"

max_tokens: 12000
temperature: 0.2
review_concurrency: 0    # 0 = auto-pick per provider
inline_comments: true
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NVIDIA_API_KEY` | Nvidia NIM API key (free at build.nvidia.com) |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `GITHUB_TOKEN` | GitHub token for PR comments |
| `GITHUB_REPOSITORY` | Repository in `owner/repo` format |
| `PR_NUMBER` | PR number (alternative to `--pr`) |

---

## GitHub Actions

Inspectra runs on every PR via GitHub Actions. Three options:

| Option | Runner | Cost | Privacy |
|--------|--------|------|---------|
| Self-hosted + Ollama | Your machine | Free | Fully private |
| Nvidia NIM cloud | GitHub-hosted | Free | Private to your account |
| OpenAI cloud | GitHub-hosted | Paid | Sends code to OpenAI |

**➜ Full workflow YAMLs:** [docs/github-actions.md](docs/github-actions.md)

**➜ Self-hosted runner setup:** [docs/self-hosted-runner.md](docs/self-hosted-runner.md)

---

## Features

- **File context** — LLM sees ±20 lines around each change, not just the diff
- **PR intent** — LLM knows whether it's a security fix, refactor, or new feature
- **Deterministic analyzers** — built-in regex + optional Bandit and Semgrep, fed into the LLM for confirmation
- **Cross-file review** — second LLM pass catches caller/callee mismatches across files
- **Language-specific rules** — 11 languages get curated antipattern checklists
- **Baseline suppression** — record false positives so they're never reported again
- **Model-aware chunk sizing** — uses the full context window (6× fewer LLM calls)
- **GitHub suggestion blocks** — one-click "Apply suggestion" buttons in the PR UI
- **Inline PR comments** — findings posted at the exact line, not just in a summary

**➜ Full feature documentation:** [docs/features.md](docs/features.md)

---

## Architecture

```
git diff
  └─► diff parser → file filter → chunk_diff_by_file (model-aware size)
        │
        ├─► build_file_context() — ±20 line window
        ├─► extract_changed_signatures() — related changes
        ├─► analyzer_registry.analyze_file() — Bandit/Semgrep/regex
        ├─► get_language_rules() — Python/JS/Go antipatterns
        │
        └─► ChunkReviewer.review() — structured JSON output, retry on failure
              │
              └─► ReviewResult[]
                    ├─► run_cross_file_review() — second LLM pass
                    ├─► apply_baseline() — suppress false positives
                    └─► output (Console / Markdown / SARIF / GitHub PR)
```

**➜ Full architecture documentation:** [docs/architecture.md](docs/architecture.md)

---

## Development

```bash
git clone https://github.com/iamakashsoni/inspectra.git
cd inspectra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/ -v           # 153 tests, all passing
python scripts/smoke_test.py  # end-to-end demo, no live LLM needed
ruff check src/ tests/     # lint
mypy src/                  # type check
```

---

## Documentation

| Document | Contents |
|----------|----------|
| [docs/llm-providers.md](docs/llm-providers.md) | Detailed setup for all 5 providers + self-hosted NIM + on-prem proxy |
| [docs/github-actions.md](docs/github-actions.md) | Ready-to-use workflow YAMLs (Ollama, Nvidia, OpenAI, CI) |
| [docs/self-hosted-runner.md](docs/self-hosted-runner.md) | Complete self-hosted runner setup guide (6 steps + troubleshooting) |
| [docs/publishing-to-pypi.md](docs/publishing-to-pypi.md) | Complete PyPI publishing guide (account → OIDC → releases → updates) |
| [docs/features.md](docs/features.md) | Detailed feature documentation with how/why for each |
| [docs/architecture.md](docs/architecture.md) | System architecture, module map, design decisions |

---

## License

Licensed under the **MIT License** — see [LICENSE](LICENSE).

Copyright © 2025-2026 **Akash Soni**. All rights reserved.

You may fork, modify, and distribute this project with proper attribution to the original author. You may **not**:
- Claim authorship of the original work
- Use the author's name to endorse derived products without explicit permission
- Remove or alter the copyright notices in the source files

Every source file includes a copyright header. Redistributions must retain these notices.

---

## Author

<div align="center">

**Akash Soni**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/iamakashsoni/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/iamakashsoni)
[![PyPI](https://img.shields.io/badge/PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/inspectra/)

*Building self-hosted developer tools that keep your code private.*

⭐ If this project helped you, consider giving it a star!

</div>
