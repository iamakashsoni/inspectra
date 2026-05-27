# 🔍 Inspectra

**AI-powered code review engine for pull requests.**

[![CI](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml/badge.svg)](https://github.com/iamakashsoni/inspectra/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/inspectra.svg)](https://pypi.org/project/inspectra/)
[![Python](https://img.shields.io/pypi/pyversions/inspectra.svg)](https://pypi.org/project/inspectra/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Inspectra reviews your git diffs using LLMs — locally via **Ollama** (free, private) or via **OpenAI / Anthropic** — and posts structured, actionable feedback directly on your GitHub PR.

```
$ inspectra review --provider ollama

Found 3 reviewable files.

🔴 [CRITICAL] SQL Injection
  File: auth/service.py — Line 42
  User input is directly concatenated into the SQL query.
  Suggested fix: Use parameterised queries instead of string interpolation.

🟠 [HIGH] Missing Error Handling
  File: api/client.py — Line 88
  Network request does not handle timeout or connection failures.
  Suggested fix: Wrap in try/except and add retry logic.
```

---

## Features

- **Reviews only changed code** — parses the git diff, never sends your whole repo
- **Multi-provider** — Ollama (local/free), OpenAI, Anthropic; all behind one interface
- **Structured findings** — every issue has severity, category, explanation, and a fix
- **GitHub integration** — posts PR comments, submits reviews (approve / request changes)
- **SARIF export** — compatible with GitHub Code Scanning
- **Response caching** — skip re-reviewing unchanged hunks (`--cache`)
- **Token-safe chunking** — large diffs are split at hunk boundaries
- **GitHub Actions ready** — self-hosted (Ollama) and cloud (OpenAI) workflows included

---

## Quick Start

### Install

```bash
pip install inspectra
```

### Review with Ollama (free, local)

```bash
# Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen2.5-coder:14b

# Review your uncommitted changes
inspectra review
```

### Review with OpenAI

```bash
export OPENAI_API_KEY=sk-...
inspectra review --provider openai --model gpt-4o-mini
```

### Review a GitHub PR

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=myorg/myrepo

inspectra review --pr 42 --post-comment
```

### Generate config file

```bash
inspectra init     # creates .inspectra.yml in the current directory
```

---

## CLI Reference

```
Commands:
  review        Review the current git diff or a GitHub PR
  init          Create a default .inspectra.yml
  models        List available Ollama models
  cache-clear   Clear the local LLM response cache
  version       Show version

review options:
  -p, --provider          ollama | openai | anthropic  [default: ollama]
  -m, --model             Model name
  -c, --config            Path to .inspectra.yml
  -o, --output            Write Markdown report to file
      --sarif             Write SARIF report (for GitHub Code Scanning)
      --pr                GitHub PR number
      --post-comment      Post review as a GitHub PR comment
      --pr-summary        Generate AI PR-level summary  [default: on]
      --staged            Review staged changes only
      --cache             Cache LLM responses to .inspectra_cache/
      --dry-run           Parse diff without calling the LLM
      --fail-on-high      Exit 1 when critical/high issues found  [default: on]
  -v, --verbose           Enable verbose logging
```

---

## GitHub Actions

### Option A — Ollama on a Self-Hosted Runner (Recommended)

Free, private — your code never leaves your network.

```yaml
# .github/workflows/inspectra.yml
name: Inspectra Review

on:
  pull_request:

jobs:
  inspectra:
    runs-on: self-hosted   # your machine with Ollama installed

    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install inspectra

      - run: ollama serve & sleep 3

      - run: |
          inspectra review \
            --provider ollama \
            --model qwen2.5-coder:14b \
            --post-comment \
            --pr ${{ github.event.pull_request.number }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
```

**Self-hosted runner setup:** Repo/Org → Settings → Actions → Runners → New runner. Follow the install script, then run `./svc.sh install && ./svc.sh start` to keep it alive across reboots.

### Option B — OpenAI on GitHub-Hosted Runner

```yaml
      - run: |
          inspectra review \
            --provider openai \
            --model gpt-4o-mini \
            --post-comment \
            --pr ${{ github.event.pull_request.number }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
```

### SARIF + GitHub Code Scanning

```yaml
      - run: inspectra review --sarif inspectra.sarif

      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: inspectra.sarif
```

---

## Configuration

Create `.inspectra.yml` in your repository root (or run `inspectra init`):

```yaml
provider: ollama
model: qwen2.5-coder:14b

ollama:
  host: http://localhost:11434
  timeout: 300

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
  - "*.min.js"
  - "vendor/*"

max_tokens: 12000
max_chunk_tokens: 3000
temperature: 0.2
```

---

## Environment Variables

| Variable              | Description                                  |
|-----------------------|----------------------------------------------|
| `OPENAI_API_KEY`      | OpenAI API key                               |
| `ANTHROPIC_API_KEY`   | Anthropic API key                            |
| `GITHUB_TOKEN`        | GitHub token for PR comments                 |
| `GITHUB_REPOSITORY`   | Repository in `owner/repo` format            |
| `PR_NUMBER`           | PR number (alternative to `--pr`)            |

Copy `.env.example` to `.env` and fill in your values — it is gitignored.

---

## Recommended Ollama Models

| Model                | RAM needed | Best for                     |
|----------------------|-----------|------------------------------|
| `qwen2.5-coder:7b`   | 8 GB      | Fast, lightweight CI         |
| `qwen2.5-coder:14b`  | 16 GB     | Default — best balance       |
| `deepseek-coder:16b` | 20 GB     | Deeper analysis              |
| `qwen2.5-coder:32b`  | 40 GB     | Enterprise-grade reviews     |

---

## Development

```bash
git clone https://github.com/iamakashsoni/inspectra
cd inspectra
pip install -e ".[dev]"

make test        # run tests
make lint        # lint
make check       # lint + types + tests
make review      # dry-run review of the repo itself
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full contribution guide.

---

## Architecture

```
git diff
  └─► diff parser (unidiff)
        └─► file filter (skip locks, minified, binary)
              └─► token chunker (hunk-level splitting)
                    └─► LLM provider (Ollama / OpenAI / Anthropic)
                          └─► response parser → ReviewResult[]
                                └─► output (console / Markdown / SARIF / PR comment)
```

See [docs/architecture.md](docs/architecture.md) for the full diagram.

---

## License

MIT — see [LICENSE](LICENSE).
