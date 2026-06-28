# GitHub Actions

Inspectra ships with ready-to-use GitHub Actions workflows. Pick the one that matches your provider and runner setup.

---

## Self-hosted with Ollama (free, fully private)

Your code never leaves your network. Requires a self-hosted runner with Ollama installed — see [Self-Hosted Runner Setup](self-hosted-runner.md).

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

**Key features:**
- `paths-ignore` skips reviews for docs-only PRs
- `concurrency` cancels in-flight runs when a new commit lands
- `continue-on-error: true` fails open (doesn't block PRs if Ollama is down)
- `--cache` reuses cached responses across runs
- SARIF uploaded to GitHub Code Scanning

---

## Cloud with Nvidia NIM (free — no self-hosted runner)

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

**Required secret:** `NVIDIA_API_KEY` — add it under Settings → Secrets and variables → Actions → New repository secret.

---

## Cloud with OpenAI (paid)

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

**Required secret:** `OPENAI_API_KEY`.

---

## CI workflow (runs on every push and PR)

The CI workflow runs tests and linting on every push and PR. It also includes a dry-run self-review of Inspectra on its own diff.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    paths-ignore:
      - '**/*.md'
      - 'docs/**'

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check src/ tests/

      - name: Run tests
        run: pytest --cov=inspectra --cov-report=xml -q

      - name: Inspectra self-review (dry-run)
        run: inspectra review --dry-run --no-pr-summary --no-fail-on-high
        continue-on-error: true

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
        continue-on-error: true
```

---

## Adding secrets

For cloud provider workflows, add the API key as a repository secret:

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. **New repository secret**
3. Name: `NVIDIA_API_KEY` (or `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`)
4. Value: your API key
5. **Add secret**

The `GITHUB_TOKEN` is automatically injected by GitHub Actions — you don't need to create it.
