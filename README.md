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

- [How It Works](#how-it-works)
- [LLM Providers](#llm-providers)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [GitHub Actions](#github-actions)
- [Features](#features)
- [Self-Hosted Runner Setup](#self-hosted-runner-setup)
- [Publishing to PyPI](#publishing-to-pypi)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)
- [Author](#author)

---

## How It Works

```
$ inspectra review --provider nvidia --post-comment --pr 42

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

| Provider | Default model | Concurrency | Free | Private | Setup |
|----------|---------------|:-----------:|:----:|:-------:|-------|
| `ollama` | `qwen2.5-coder:14b` | 3 | ✅ | ✅ | Local install |
| `nvidia` | `meta/llama-3.3-70b-instruct` | 5 | ✅ | ✅* | Free API key |
| `openai` | `gpt-4o-mini` | 10 | ❌ | ❌ | Paid API key |
| `anthropic` | `claude-sonnet-4-20250514` | 8 | ❌ | ❌ | Paid API key |
| `openrouter` | `anthropic/claude-3.5-sonnet` | 5 | ❌ | ❌ | Paid API key |

\* Nvidia cloud is private to your account; self-hosted NIM is fully air-gapped.

### Nvidia NIM (free cloud — recommended)

Free cloud access to production-grade models at [build.nvidia.com](https://build.nvidia.com) — no GPU or Docker needed.

**Step 1 — Get a free API key:**
1. Open [build.nvidia.com](https://build.nvidia.com)
2. Sign in → **Get API Key** (starts with `nvapi-`)

**Step 2 — Review:**
```bash
export NVIDIA_API_KEY=nvapi-...
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct
```

**Popular free models:**

| Model | Best for |
|-------|----------|
| `meta/llama-3.3-70b-instruct` | **Default — best balance for code review** |
| `deepseek-ai/deepseek-r1` | Deep reasoning, complex bugs |
| `mistralai/mistral-large-2411` | Fast, strong general-purpose |
| `qwen/qwen2.5-coder-32b-instruct` | Code-specialized |
| `microsoft/phi-4` | Lightweight, fast |

Browse the full catalog at [build.nvidia.com/models](https://build.nvidia.com/models).

### Ollama (free, fully local)

Runs on your hardware — code never leaves your network.

**Step 1 — Install Ollama:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5-coder:14b
```

**Step 2 — Review:**
```bash
inspectra review
```

**Recommended models:**

| Model | RAM | Best for |
|-------|-----|----------|
| `qwen2.5-coder:7b` | 8 GB | Fast CI |
| `qwen2.5-coder:14b` | 16 GB | **Default — best balance** |
| `deepseek-coder:16b` | 20 GB | Deeper analysis |
| `qwen2.5-coder:32b` | 40 GB | Enterprise-grade |

### OpenAI / Anthropic / OpenRouter (paid cloud)

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
inspectra review --provider openai --model gpt-4o-mini

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
inspectra review --provider anthropic --model claude-sonnet-4-20250514

# OpenRouter (aggregator — one key, many models)
export OPENROUTER_API_KEY=sk-or-...
inspectra review --provider openrouter --model anthropic/claude-3.5-sonnet
```

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

## Quick Start

### Install

```bash
pip install inspectra
```

### Review your local changes

```bash
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct
```

### Review a GitHub PR

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=myorg/myrepo

inspectra review --provider nvidia --pr 42 --post-comment
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
provider: nvidia
model: meta/llama-3.3-70b-instruct

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
| `NVIDIA_API_KEY` | Nvidia NIM API key (free at build.nvidia.com) |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `GITHUB_TOKEN` | GitHub token for PR comments |
| `GITHUB_REPOSITORY` | Repository in `owner/repo` format |
| `PR_NUMBER` | PR number (alternative to `--pr`) |

---

## GitHub Actions

### Self-hosted with Ollama (free, fully private)

Your code never leaves your network. Requires a self-hosted runner with Ollama installed (see [Self-Hosted Runner Setup](#self-hosted-runner-setup)).

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

### Cloud with Nvidia NIM (free — no self-hosted runner)

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

---

## Features

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

The Ollama workflow runs on a self-hosted runner — your own machine with Ollama installed. This keeps code fully private (never leaves your network) and is free (no API costs). This guide covers the full setup from scratch.

### Prerequisites

- A machine that's always on (or wakes on PR events) — a home server, cloud VM, or office workstation
- Linux x86_64 (recommended), macOS, or Windows
- ≥16 GB RAM for 14B models, ≥32 GB for 32B models
- GPU optional but strongly recommended (Nvidia with CUDA, or Apple Silicon)
- Admin/sudo access for installing Ollama as a service

### Step 1 — Create the runner on GitHub

1. Go to your repository on GitHub
2. **Settings → Actions → Runners → New self-hosted runner**
3. Select your OS (Linux x64 for this guide)
4. GitHub shows a registration token — copy it (it's valid for ~1 hour)

### Step 2 — Install the runner software

On your runner machine:

```bash
# Create a directory for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the runner (check GitHub for the latest version)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz

# Extract
tar xzf actions-runner-linux-x64.tar.gz

# Configure — use the token from Step 1
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# When prompted:
# - Runner group: press Enter (default)
# - Runner name: inspectra-runner (or any name)
# - Labels: inspectra,ollama  (type these, press Enter after each, blank line to finish)
# - Work folder: press Enter (default _work)
```

### Step 3 — Install as a system service (starts on boot)

```bash
sudo ./svc.sh install
sudo ./svc.sh start

# Verify it's running
sudo ./svc.sh status

# Check it shows as "Idle" (green) on GitHub:
# Settings → Actions → Runners → your runner should say "Idle"
```

To uninstall later: `sudo ./svc.sh stop && sudo ./svc.sh uninstall`

### Step 4 — Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Enable as a service (starts on boot, runs on port 11434)
sudo systemctl enable --now ollama

# Pull the review model (this takes a few minutes — ~8 GB download)
ollama pull qwen2.5-coder:14b

# Verify
ollama list
# Should show: qwen2.5-coder:14b

# Verify the API is reachable
curl http://localhost:11434/api/tags
# Should return JSON with the model list
```

### Step 5 — Add the workflow file

In your repository, create `.github/workflows/inspectra.yml` using the workflow from the [GitHub Actions](#github-actions) section above (the "Self-hosted with Ollama" tab).

### Step 6 — Test it

1. Open a pull request against your repository
2. Within a few seconds, the runner should pick up the `Inspectra Review (Ollama)` job
3. Check the Actions tab for logs
4. Once complete, the review appears as a comment on the PR

### Verification checklist

- [ ] Runner shows **Idle** (green) under Settings → Actions → Runners
- [ ] `curl http://localhost:11434/api/tags` returns JSON on the runner machine
- [ ] `ollama list` shows `qwen2.5-coder:14b`
- [ ] Opening a PR triggers the `Inspectra Review (Ollama)` workflow
- [ ] Review comment appears on the PR within ~2 minutes

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Runner shows "offline" | `sudo ./svc.sh status` on the runner machine; if stopped, `sudo ./svc.sh start` |
| Runner shows "offline" after reboot | Service not enabled: `sudo ./svc.sh install && sudo ./svc.sh start` |
| Ollama not reachable | `curl http://localhost:11434/api/tags` — if it fails, `sudo systemctl restart ollama` |
| Model not pulled | `ollama list` — if empty, `ollama pull qwen2.5-coder:14b` |
| Out of memory | Use a smaller model: `ollama pull qwen2.5-coder:7b`, update `--model` in workflow |
| GPU not used | `ollama ps` should show GPU — if CPU-only, install [CUDA](https://docs.nvidia.com/cuda/) |
| Workflow doesn't trigger | Check `paths-ignore` in the workflow — PRs touching only `.md`/docs are skipped |
| Review step fails but PR is open | `continue-on-error: true` is set — check the Actions logs for the error |
| First run is slow | Ollama loads the model into memory on first call (~30-60s). Subsequent calls are fast. |

### Updating the runner

```bash
cd ~/actions-runner
sudo ./svc.sh stop
# Download the new version (check GitHub for latest)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.318.0/actions-runner-linux-x64-2.318.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz
sudo ./svc.sh start
```

### Updating Ollama models

```bash
# Update Ollama itself
curl -fsSL https://ollama.com/install.sh | sh

# Pull a newer model version
ollama pull qwen2.5-coder:14b   # re-pulls if there's an update

# Remove an old model to free disk
ollama rm qwen2.5-coder:7b
```

### Security notes

- The runner executes workflow code from your repository. Only register it on repos you trust.
- The `GITHUB_TOKEN` secret is automatically injected by GitHub Actions — you don't need to create it.
- Ollama listens on `localhost:11434` only (not exposed to the network) by default.
- Runner logs may contain diff content — store them securely if your repo is private.

---

## Publishing to PyPI

This guide covers the complete PyPI publishing workflow — from creating a PyPI account to pushing version updates. Inspectra uses **GitHub OIDC trusted publishing**, which means no API tokens to manage: GitHub authenticates to PyPI via OpenID Connect.

### Prerequisites

- A [GitHub](https://github.com) account (you have one)
- A [PyPI](https://pypi.org) account
- Maintainer access to the `iamakashsoni/inspectra` repository
- The `publish.yml` workflow (already in `.github/workflows/`)

### Step 1 — Create a PyPI account

1. Go to [pypi.org/account/register](https://pypi.org/account/register/)
2. Sign up with your email and a strong password
3. **Enable two-factor authentication** (required since 2023):
   - Account settings → 2FA → set up TOTP (Google Authenticator, Authy, etc.)
   - Save recovery codes in a password manager

### Step 2 — Reserve the project name (first release only)

If this is the first release of `inspectra`:

1. Build the package locally:
   ```bash
   python -m pip install --upgrade build
   python -m build
   ```
   This creates `dist/inspectra-0.2.0-py3-none-any.whl` and `dist/inspectra-0.2.0.tar.gz`.

2. Upload to PyPI manually (one-time, to claim the name):
   ```bash
   python -m pip install --upgrade twine
   python -m twine upload dist/*
   ```
   You'll be prompted for your PyPI username and password (use an API token, not your password — see below).

3. Create an API token for the initial upload:
   - PyPI → Account settings → API tokens → Add API token
   - Scope: "Entire account" (for the first upload only)
   - Copy the token (starts with `pypi-`) — you won't see it again
   - Username: `__token__`, Password: `pypi-...` (the token you just copied)

After the first release, all subsequent publishes go through GitHub Actions via OIDC — no API tokens needed.

### Step 3 — Configure trusted publishing on PyPI

This connects your GitHub repo to your PyPI project so GitHub Actions can publish without a token.

1. Go to [pypi.org](https://pypi.org) → your account → **Account settings** → **Publishing** (or the [Publishing](https://pypi.org/manage/account/publishing/) page directly)
2. Scroll to **Add a new publisher**
3. Select **GitHub**
4. Fill in:
   - **PyPI Project Name:** `inspectra`
   - **Owner:** `iamakashsoni`
   - **Repository name:** `inspectra`
   - **Workflow filename:** `publish.yml`
   - **Environment name:** `pypi`
5. Click **Add**

PyPI now trusts publishes that come from `iamakashsoni/inspectra` via the `publish.yml` workflow running in the `pypi` environment.

### Step 4 — Create the `pypi` environment in GitHub

1. Go to your repo on GitHub
2. **Settings → Environments → New environment**
3. Name it `pypi` (must match what you entered on PyPI)
4. (Optional) Add required reviewers: under "Required reviewers", add yourself — this gives you a manual approve step before each publish
5. Save

### Step 5 — Verify the workflow file

Confirm `.github/workflows/publish.yml` exists and looks like this:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'   # Triggers on tags like v0.2.0, v1.0.0

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi              # must match the environment from Step 4
    timeout-minutes: 10
    permissions:
      id-token: write              # required for OIDC trusted publishing
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

### Step 6 — Publish your first release

1. Update the version in `pyproject.toml`:
   ```bash
   # For a patch release (0.2.0 → 0.2.1)
   sed -i 's/version = "0.2.0"/version = "0.2.1"/' pyproject.toml

   # For a minor release (0.2.1 → 0.3.0)
   sed -i 's/version = "0.2.1"/version = "0.3.0"/' pyproject.toml

   # For a major release (0.3.0 → 1.0.0)
   sed -i 's/version = "0.3.0"/version = "1.0.0"/' pyproject.toml
   ```

2. Update `CHANGELOG.md` with what changed under a new `[Unreleased]` → `[0.2.1]` heading.

3. Commit and tag:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "bump: v0.2.1"
   git tag v0.2.1
   git push origin main --tags
   ```

4. The tag push triggers the `publish.yml` workflow:
   - Go to the **Actions** tab to watch it run
   - If you added a required reviewer (Step 4), you'll get a notification to approve
   - The workflow builds the package and uploads to PyPI via OIDC
   - No API token is used — GitHub authenticates via OIDC

5. Verify the release:
   - Go to [pypi.org/project/inspectra](https://pypi.org/project/inspectra/)
   - The new version should appear within a minute
   - Install it: `pip install inspectra==0.2.1`

### Step 7 — Create a GitHub Release (optional, recommended)

After the PyPI publish succeeds, create a GitHub Release for visibility:

1. Go to your repo → **Releases → Draft a new release**
2. **Choose a tag:** `v0.2.1` (the tag you pushed)
3. **Release title:** `v0.2.1`
4. **Description:** paste the changelog entry for this version
5. **Publish release**

### Pushing subsequent updates

For every future release, repeat Step 6:

```bash
# 1. Bump version
sed -i 's/version = "0.2.1"/version = "0.2.2"/' pyproject.toml

# 2. Update CHANGELOG.md with what's new

# 3. Commit, tag, push
git add pyproject.toml CHANGELOG.md
git commit -m "bump: v0.2.2"
git tag v0.2.2
git push origin main --tags

# 4. Watch the Actions tab — the publish workflow runs automatically
# 5. Verify on pypi.org/project/inspectra
```

### Version bumping rules (Semantic Versioning)

| Bump type | When to use | Example |
|-----------|-------------|---------|
| **Patch** (0.2.1 → 0.2.2) | Bug fixes, no new features | Fix inline comment posting |
| **Minor** (0.2.2 → 0.3.0) | New features, backward-compatible | Add a new provider |
| **Major** (0.3.0 → 1.0.0) | Breaking changes | Change CLI flag names |

### Yanking a bad release

If a release is broken but you don't want to delete it:

```bash
pip install twine
python -m twine yank inspectra==0.2.1
```

Yanked versions stay downloadable but don't show up in `pip install inspectra` (pip picks the latest non-yanked).

### Troubleshooting PyPI publishing

| Problem | Fix |
|---------|-----|
| `Workflow does not have permissions` | Ensure `permissions: id-token: write` is in the workflow |
| `Environment 'pypi' not found` | Create the environment in GitHub repo Settings → Environments |
| `Publisher not configured` | Redo Step 3 on PyPI — check owner/repo/workflow name match exactly |
| `File already exists` | You can't re-upload the same version. Bump the version and try again. |
| Build fails | Run `python -m build` locally first to debug |
| Tag didn't trigger workflow | Ensure the tag starts with `v` (e.g. `v0.2.1`, not `0.2.1`) |

---

## Architecture

```
git diff
  └─► diff parser (unidiff)
        └─► file filter (skip locks, minified, binary)
              └─► chunk_diff_by_file (model-aware size)
                    │
                    ├─► build_file_context() — read full file, ±20 line window
                    ├─► extract_changed_signatures() — for related-changes block
                    ├─► analyzer_registry.analyze_file() — Bandit/Semgrep/regex
                    ├─► get_language_rules() — Python/JS/Go antipatterns
                    │
                    └─► ChunkReviewer.review()
                          │   ├── prompt includes: file context, PR intent,
                          │   │   related changes, analyzer findings, language rules
                          │   ├── structured JSON output (schema-enforced)
                          │   └── retry on parse failure + transient network errors
                          │
                          └─► ReviewResult[]
                                │
                                ├─► run_cross_file_review() — second LLM pass
                                │
                                ├─► apply_baseline() — suppress false positives
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
