# 🔍 Inspectra

**Self-hosted AI code reviewer for pull requests.**

Reviews your git diffs with LLMs — locally via **Ollama** (free, private) or via **OpenAI / Anthropic / Nvidia NIM / OpenRouter** — and posts structured, actionable feedback directly on your GitHub PR.

[![CI](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml/badge.svg)](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/inspectra.svg)](https://pypi.org/project/inspectra/)
[![Python](https://img.shields.io/pypi/pyversions/inspectra.svg)](https://pypi.org/project/inspectra/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/iamakashsoni/inspectra/pulls)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

> **It reviews your code** — bugs, security vulnerabilities, performance issues, architectural concerns.
> **It does not just find syntax errors** — it understands the surrounding code, the PR intent, and cross-file dependencies to give you precise, actionable suggestions.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [LLM Providers](#llm-providers)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [GitHub Actions](#github-actions)
- [Phase 2 Features](#phase-2-features)
- [Self-Hosted Runner Setup](#self-hosted-runner-setup)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)
- [Author](#author)

---

## Quick Start

### Install

```bash
pip install inspectra
```

### Option A — Nvidia NIM (free cloud, fastest start)

Get a free API key at [build.nvidia.com](https://build.nvidia.com), then:

```bash
export NVIDIA_API_KEY=nvapi-...
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct
```

No GPU, no Docker, no local setup. Uses a 70B model for free.

### Option B — Ollama (free, fully local, private)

```bash
# Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5-coder:14b

# Review your uncommitted changes
inspectra review
```

### Option C — OpenAI / Anthropic (paid cloud)

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
inspectra review --provider openai --model gpt-4o-mini

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
inspectra review --provider anthropic --model claude-sonnet-4-20250514
```

### Review a GitHub PR

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=myorg/myrepo

inspectra review --provider nvidia --pr 42 --post-comment
```

---

## Get a free Nvidia API key

Nvidia offers **free cloud access** to production-grade models (Llama 3.3 70B, DeepSeek-R1, Mistral, Qwen, Phi, and more) via [build.nvidia.com](https://build.nvidia.com) — no GPU or Docker required.

1. Open [build.nvidia.com](https://build.nvidia.com)
2. Sign in with an Nvidia account → **Get API Key** (starts with `nvapi-`)
3. Pick a model from the catalog (e.g. `meta/llama-3.3-70b-instruct`)
4. Review:

```bash
export NVIDIA_API_KEY=nvapi-...
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct
```

This is the easiest way to get high-quality reviews without running Ollama locally or paying for OpenAI/Anthropic.

---

## How It Works

```
$ inspectra review --provider ollama --post-comment --pr 42

Found 3 reviewable file(s).

🔴 [CRITICAL] SQL Injection in user lookup
  File: auth/service.py — Line 42
  Rule: SQL_INJECTION
  Suggested fix:
    ```suggestion
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    ```

🟠 [HIGH] Missing error handling on DB connection
  File: auth/service.py — Line 40
  Rule: MISSING_ERROR_HANDLING
```

Inspectra:

1. Parses the git diff (local or via GitHub API)
2. Filters out lock files, binaries, minified code, generated files
3. Chunks the diff at hunk boundaries (model-aware size — uses the full context window)
4. For each chunk:
   - Reads the full file content around the change (±20 lines) for context
   - Runs deterministic analyzers (Bandit, Semgrep, built-in regex) and feeds their findings to the LLM
   - Sends the diff + context + PR intent + related changes to the LLM
5. Parses the structured JSON response into `ReviewIssue` objects
6. Runs a second-pass cross-file consistency check
7. Posts the review as a PR comment + inline comments at issue lines (with one-click "Apply suggestion" buttons)

---

## LLM Providers

Five providers, one interface. Switch with `--provider`, no code changes.

| Provider | Default model | Default concurrency | Free | Private |
|----------|---------------|---------------------|:----:|:-------:|
| `ollama` | `qwen2.5-coder:14b` | 3 | ✅ | ✅ |
| `nvidia` | `meta/llama-3.3-70b-instruct` | 5 | ✅ | ✅ (self-hosted NIM) |
| `openai` | `gpt-4o-mini` | 10 | ❌ | ❌ |
| `anthropic` | `claude-sonnet-4-20250514` | 8 | ❌ | ❌ |
| `openrouter` | `anthropic/claude-3.5-sonnet` | 5 | ❌ | ❌ |

### Nvidia NIM (free cloud)

Nvidia provides **free cloud API access** at [build.nvidia.com](https://build.nvidia.com) to dozens of production-grade models — Llama 3.3 70B, DeepSeek-R1, Mistral Large, Qwen, Phi, and more. No GPU, no Docker, no credit card to start.

```bash
# 1. Get a free API key at https://build.nvidia.com
export NVIDIA_API_KEY=nvapi-...

# 2. Review with a 70B model — free
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct

# Or try DeepSeek-R1 for deeper reasoning
inspectra review --provider nvidia --model deepseek-ai/deepseek-r1
```

**Popular free models on Nvidia cloud:**

| Model | Best for |
|-------|----------|
| `meta/llama-3.3-70b-instruct` | **Default — best balance for code review** |
| `deepseek-ai/deepseek-r1` | Deep reasoning, complex bugs |
| `mistralai/mistral-large-2411` | Fast, strong general-purpose |
| `qwen/qwen2.5-coder-32b-instruct` | Code-specialized |
| `microsoft/phi-4` | Lightweight, fast |

Browse the full catalog at [build.nvidia.com](https://build.nvidia.com/models).

### Self-hosted NIM (air-gapped, on-prem)

For enterprises that need fully air-gapped reviews, run a NIM container locally:

```bash
docker run --gpus all -p 8000:8000 nvcr.io/nim/meta/llama-3.3-70b-instruct:latest

inspectra review --provider nvidia \
  --base-url http://localhost:8000/v1 \
  --model meta/llama-3.3-70b-instruct
```

### On-prem OpenAI proxy

Any OpenAI-compatible endpoint works:

```bash
inspectra review --provider openai --base-url https://internal-proxy.company.com/v1
```

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
provider: ollama
model: qwen2.5-coder:14b

ollama:
  host: http://localhost:11434
  timeout: 300

# Cloud provider keys (or use env vars)
# openai_api_key: sk-...
# anthropic_api_key: sk-ant-...
# nvidia_api_key: nvapi-...
# openrouter_api_key: sk-or-...

# Self-hosted endpoint overrides
# nvidia_base_url: http://localhost:8000/v1   # self-hosted NIM
# openai_base_url: https://internal-proxy.company.com/v1

review:
  security: true
  bugs: true
  performance: true
  maintainability: true
  architecture: true
  concurrency: true
  scalability: true

exclude:
  - "*.lock"
  - "dist/*"
  - "vendor/*"

max_tokens: 12000
max_chunk_tokens: 3000        # overridden by model-aware sizing when model is known
temperature: 0.2

# 0 = auto-pick per provider (Ollama=3, OpenAI=10, Anthropic=8, Nvidia=5, OpenRouter=5)
review_concurrency: 0

# Post inline comments at issue lines when reviewing a PR
inline_comments: true
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `NVIDIA_API_KEY` | Nvidia NIM API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `GITHUB_TOKEN` | GitHub token for PR comments |
| `GITHUB_REPOSITORY` | Repository in `owner/repo` format |
| `PR_NUMBER` | PR number (alternative to `--pr`) |

---

## GitHub Actions

### Self-hosted with Ollama (recommended)

Free, private — your code never leaves your network.

```yaml
# .github/workflows/inspectra.yml
name: Inspectra Review

on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths-ignore:
      - '**/*.md'
      - 'docs/**'
      - '.github/**'

concurrency:
  group: inspectra-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  inspectra:
    runs-on: self-hosted
    timeout-minutes: 15
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install 'inspectra==0.2.0'

      - name: Ensure Ollama is up and model is pulled
        run: |
          curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 || ollama serve &>/dev/null &
          for i in $(seq 1 60); do
            curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 && break
            sleep 1
          done
          ollama list | grep -q 'qwen2.5-coder:14b' || ollama pull qwen2.5-coder:14b

      - name: Run Inspectra Review
        continue-on-error: true
        run: |
          inspectra review \
            --provider ollama \
            --model qwen2.5-coder:14b \
            --post-comment --inline \
            --sarif inspectra.sarif --cache \
            --no-fail-on-high \
            --pr ${{ github.event.pull_request.number }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}

      - name: Upload SARIF to GitHub Code Scanning
        if: always() && hashFiles('inspectra.sarif') != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: inspectra.sarif
          category: inspectra
```

### Cloud with Nvidia NIM (free — no self-hosted runner needed)

The easiest cloud option: free API key from [build.nvidia.com](https://build.nvidia.com), runs on GitHub-hosted runners, uses a 70B model.

```yaml
name: Inspectra Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: inspectra-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  inspectra:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install 'inspectra==0.2.0'
      - name: Run review
        continue-on-error: true
        run: |
          inspectra review \
            --provider nvidia \
            --model meta/llama-3.3-70b-instruct \
            --post-comment --inline \
            --sarif inspectra.sarif \
            --no-fail-on-high \
            --pr ${{ github.event.pull_request.number }}
        env:
          NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
      - name: Upload SARIF
        if: always() && hashFiles('inspectra.sarif') != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: inspectra.sarif
          category: inspectra
```

### Cloud with OpenAI (paid)

```yaml
name: Inspectra Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: inspectra-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  inspectra:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install 'inspectra==0.2.0'
      - name: Run review
        continue-on-error: true
        run: |
          inspectra review \
            --provider openai \
            --model gpt-4o-mini \
            --post-comment --inline \
            --sarif inspectra.sarif \
            --no-fail-on-high \
            --pr ${{ github.event.pull_request.number }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
      - name: Upload SARIF
        if: always() && hashFiles('inspectra.sarif') != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: inspectra.sarif
          category: inspectra
```

### Publishing to PyPI

Inspectra uses GitHub OIDC trusted publishing — no API tokens needed.

1. **The workflow is already in `.github/workflows/publish.yml`:**

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'   # Triggers on tags like v0.2.0, v1.0.0

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    timeout-minutes: 10
    permissions:
      id-token: write    # Required for trusted publishing (OIDC)
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          python -m pip install --upgrade pip
          pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

2. **Configure trusted publishing on PyPI:**
   - Go to [pypi.org](https://pypi.org) → your account → **Publishing** → **Add a new publisher**
   - Select **GitHub**
   - PyPI project name: `inspectra`
   - Owner: `iamakashsoni`
   - Repository name: `inspectra`
   - Workflow filename: `publish.yml`
   - Environment name: `pypi`

3. **Create an environment** in your GitHub repo:
   - Settings → Environments → New environment → name it `pypi`

4. **Publish a release:**

```bash
# Update version in pyproject.toml
sed -i 's/version = "0.2.0"/version = "0.2.1"/' pyproject.toml
git commit -am "bump: v0.2.1"
git tag v0.2.1
git push origin main --tags
```

The `publish.yml` workflow runs automatically on the tag push and publishes to PyPI via OIDC — no `PYPI_API_TOKEN` secret needed.

---

## Phase 2 Features

### File context

The LLM sees ±20 lines around each change, not just the diff. This lets it understand the function's purpose and surrounding patterns.

### PR intent

The LLM knows whether it's reviewing a security fix, a refactor, or a new feature — calibrating its review accordingly. Auto-extracted from the PR title, or set via `--pr-intent`.

### Deterministic analyzers

Built-in regex analyzer (always available, no deps) plus optional Bandit and Semgrep wrappers. Findings are fed INTO the LLM prompt for confirmation/enrichment — best of both worlds.

| Analyzer | Languages | Install | What it catches |
|----------|-----------|---------|-----------------|
| Regex (built-in) | All | — | `eval()`, `pickle.loads()`, `shell=True`, SQL injection, hardcoded secrets, bare `except:`, mutable default args, `dangerouslySetInnerHTML` |
| Bandit | Python | `pip install bandit` | Full Bandit rule set (B101-B999) |
| Semgrep | All | `pip install semgrep` | Full Semgrep rule registry |

### Cross-file review

After the per-file pass, a second LLM call looks at all changed signatures across all files for caller/callee mismatches.

### Language-specific rules

11 languages get curated antipattern checklists in the prompt (Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP, C#, C, C++).

### Baseline suppression

Record false positives so they're never reported again:

```bash
# Suppress a rule globally
inspectra suppress SQL_INJECTION --reason "Known legacy issue"

# Suppress in a specific file
inspectra suppress BANDIT/B608 --file auth/legacy.py --reason "Legacy admin panel"

# Suppress with expiry
inspectra suppress XSS --expires 2026-12-31

# View all suppressions
inspectra baseline-show

# Apply during review
inspectra review --baseline .inspectra-baseline.json
```

### Model-aware chunk sizing

Chunks use the model's full context window (capped at 16k). A 30-file PR on `gpt-4o-mini` makes ~5 LLM calls instead of ~30 — 6× fewer calls, 6× less latency.

---

## Self-Hosted Runner Setup

The Ollama workflow requires a self-hosted runner with Ollama installed.

### 1. Set up the runner

On a machine with ≥16 GB RAM (14B models) or ≥32 GB RAM (32B models):

```bash
# Create a directory for the runner
mkdir ~/inspectra-runner && cd ~/inspectra-runner

# Download the runner (Linux x64 example)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

# Configure (get the token from your repo settings)
# Repo → Settings → Actions → Runners → New self-hosted runner
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Install as a service (starts on boot)
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Install Ollama on the runner

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Pull the review model
ollama pull qwen2.5-coder:14b

# Start Ollama as a service (runs on port 11434)
sudo systemctl enable --now ollama
```

Verify Ollama is running:

```bash
curl http://localhost:11434/api/tags
# Should return JSON with the list of pulled models
```

### 3. Verify the runner is picking up jobs

Open a PR against your repo. The runner should pick up the `Inspectra Review (Ollama)` workflow within a few seconds.

**Troubleshooting:**

| Problem | Fix |
|---------|-----|
| Runner shows "offline" | `sudo ./svc.sh status` on the runner machine |
| Ollama not reachable | `curl http://localhost:11434/api/tags` — if it fails, `sudo systemctl restart ollama` |
| Model not pulled | `ollama list` — if empty, `ollama pull qwen2.5-coder:14b` |
| Out of memory | Use a smaller model: `ollama pull qwen2.5-coder:7b` and update `--model` in the workflow |
| GPU not used | `ollama ps` should show GPU — if CPU-only, install [CUDA](https://docs.nvidia.com/cuda/) |

### 4. Recommended Ollama models

| Model | RAM needed | Best for |
|-------|-----------|----------|
| `qwen2.5-coder:7b` | 8 GB | Fast CI, lightweight reviews |
| `qwen2.5-coder:14b` | 16 GB | **Default — best balance** |
| `deepseek-coder:16b` | 20 GB | Deeper analysis |
| `qwen2.5-coder:32b` | 40 GB | Enterprise-grade reviews |

---

## Architecture

```
git diff
  └─► diff parser (unidiff)
        └─► file filter (skip locks, minified, binary)
              └─► chunk_diff_by_file (model-aware size)
                    │
                    ├─► [Phase 2] build_file_context() — read full file, ±20 line window
                    ├─► [Phase 2] extract_changed_signatures() — for related-changes block
                    ├─► [Phase 2] analyzer_registry.analyze_file() — Bandit/Semgrep/regex
                    ├─► [Phase 2] get_language_rules() — Python/JS/Go antipatterns
                    │
                    └─► ChunkReviewer.review()
                          │   ├── prompt includes: file context, PR intent,
                          │   │   related changes, analyzer findings, language rules
                          │   ├── structured JSON output (schema-enforced)
                          │   └── retry on parse failure + transient network errors
                          │
                          └─► ReviewResult[]
                                │
                                ├─► [Phase 2] run_cross_file_review() — second LLM pass
                                │
                                ├─► [Phase 2] apply_baseline() — suppress false positives
                                │
                                └─► output
                                      ├── Console (Rich tables + panels)
                                      ├── Markdown report (with GitHub suggestion blocks)
                                      ├── SARIF report (stable rule IDs → Code Scanning)
                                      └── GitHub PR comment + inline comments
```

### LLM Provider Architecture

```
BaseLLMProvider (unified interface: LLMRequest → LLMResponse)
│
├── OpenAICompatibleProvider (shared HTTP + JSON schema logic)
│   ├── OpenAIProvider        (api.openai.com)
│   ├── NvidiaProvider        (integrate.api.nvidia.com or self-hosted NIM)
│   └── OpenRouterProvider    (openrouter.ai)
│
├── AnthropicProvider         (/messages with forced tool_use for JSON)
├── OllamaProvider            (/api/chat with format=json_schema)
└── CachedProvider            (decorator over any provider)
```

Adding a 6th OpenAI-compatible provider is ~15 lines — just set the right `base_url` and default model.

---

## Development

```bash
git clone https://github.com/iamakashsoni/inspectra.git
cd inspectra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (153 tests, all passing)
pytest tests/ -v

# Run the end-to-end smoke test (no live LLM needed)
python scripts/smoke_test.py

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Project Structure

```
src/inspectra/
├── cli.py                 # Typer CLI entry point
├── config/                # Pydantic settings + YAML loader
├── git/                   # Diff parsing + file filtering
├── llm/                   # Provider abstraction + 5 implementations
├── review/
│   ├── analyzers/         # Plugin system: regex, Bandit, Semgrep
│   ├── baseline.py        # False-positive suppression
│   ├── context_builder.py # Full file context for the prompt
│   ├── cross_file.py      # Two-pass cross-file consistency check
│   ├── engine.py          # Orchestrates the review pipeline
│   ├── formatter.py       # Markdown + GitHub suggestion blocks
│   ├── prompts.py         # v4 prompt with rubric + few-shot
│   ├── reviewer.py        # ChunkReviewer with retry logic
│   └── severity.py        # ReviewIssue / ReviewResult models
├── github/                # PR diff fetch, comment posting, inline comments
├── output/                # Console, Markdown, SARIF
└── utils/                 # Logger, tokenizer, chunker, cache, language detection

tests/                     # 153 tests (one file per module)
```

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



**Akash Soni**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/iamakashsoni/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/iamakashsoni)
[![PyPI](https://img.shields.io/badge/PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/inspectra/)

*Building self-hosted developer tools that keep your code private.*



---



⭐ If this project helped you, consider giving it a star!
