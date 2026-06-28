# LLM Providers

Inspectra supports five LLM providers. Switch with `--provider`, no code changes.

## Comparison

| Provider | Default model | Concurrency | Free | Private | Setup |
|----------|---------------|:-----------:|:----:|:-------:|-------|
| `ollama` | `qwen2.5-coder:14b` | 3 | ✅ | ✅ | Local install |
| `nvidia` | `meta/llama-3.3-70b-instruct` | 5 | ✅ | ✅* | Free API key |
| `openai` | `gpt-4o-mini` | 10 | ❌ | ❌ | Paid API key |
| `anthropic` | `claude-sonnet-4-20250514` | 8 | ❌ | ❌ | Paid API key |
| `openrouter` | `anthropic/claude-3.5-sonnet` | 5 | ❌ | ❌ | Paid API key |

\* Nvidia cloud is private to your account; self-hosted NIM is fully air-gapped.

---

## Nvidia NIM (free cloud — recommended)

Free cloud access to production-grade models at [build.nvidia.com](https://build.nvidia.com) — no GPU or Docker needed.

### Step 1 — Get a free API key

1. Open [build.nvidia.com](https://build.nvidia.com)
2. Sign in with an Nvidia account
3. Click **Get API Key** (starts with `nvapi-`)

### Step 2 — Review

```bash
export NVIDIA_API_KEY=nvapi-...
inspectra review --provider nvidia --model meta/llama-3.3-70b-instruct
```

### Popular free models

| Model | Best for |
|-------|----------|
| `meta/llama-3.3-70b-instruct` | **Default — best balance for code review** |
| `deepseek-ai/deepseek-r1` | Deep reasoning, complex bugs |
| `mistralai/mistral-large-2411` | Fast, strong general-purpose |
| `qwen/qwen2.5-coder-32b-instruct` | Code-specialized |
| `microsoft/phi-4` | Lightweight, fast |

Browse the full catalog at [build.nvidia.com/models](https://build.nvidia.com/models).

### Self-hosted NIM (air-gapped)

For enterprises that need fully air-gapped reviews, run a NIM container locally:

```bash
docker run --gpus all -p 8000:8000 nvcr.io/nim/meta/llama-3.3-70b-instruct:latest

inspectra review --provider nvidia \
  --base-url http://localhost:8000/v1 \
  --model meta/llama-3.3-70b-instruct
```

---

## Ollama (free, fully local)

Runs on your hardware — code never leaves your network.

### Step 1 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
```

### Step 2 — Pull a model

```bash
ollama pull qwen2.5-coder:14b
```

### Step 3 — Review

```bash
inspectra review
```

### Recommended models

| Model | RAM | Best for |
|-------|-----|----------|
| `qwen2.5-coder:7b` | 8 GB | Fast CI |
| `qwen2.5-coder:14b` | 16 GB | **Default — best balance** |
| `deepseek-coder:16b` | 20 GB | Deeper analysis |
| `qwen2.5-coder:32b` | 40 GB | Enterprise-grade |

### Verify available models

```bash
inspectra models
```

---

## OpenAI (paid cloud)

### Setup

```bash
export OPENAI_API_KEY=sk-...
```

### Review

```bash
inspectra review --provider openai --model gpt-4o-mini
```

### Recommended models

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| `gpt-4o-mini` | Fast | Good | Low |
| `gpt-4o` | Medium | Excellent | Medium |

### On-prem OpenAI proxy

Any OpenAI-compatible endpoint works:

```bash
inspectra review --provider openai --base-url https://internal-proxy.company.com/v1
```

---

## Anthropic (paid cloud)

### Setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Review

```bash
inspectra review --provider anthropic --model claude-sonnet-4-20250514
```

### Recommended models

| Model | Notes |
|-------|-------|
| `claude-sonnet-4-20250514` | Best balance |
| `claude-haiku-4-5-20251001` | Fast and cheap |

---

## OpenRouter (paid aggregator)

One API key, access to dozens of model providers (Anthropic, OpenAI, Meta, Mistral, etc.).

### Setup

```bash
export OPENROUTER_API_KEY=sk-or-...
```

### Review

```bash
inspectra review --provider openrouter --model anthropic/claude-3.5-sonnet
```

OpenRouter model strings use the `vendor/model` format (e.g. `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `meta-llama/llama-3.3-70b-instruct`).

---

## Caching (all providers)

Enable response caching to avoid re-reviewing identical diff hunks:

```bash
inspectra review --cache
```

Responses are stored in `.inspectra_cache/` (auto-gitignored, 7-day TTL).

Clear the cache:

```bash
inspectra cache-clear
```

The cache key includes the prompt version, temperature, system prompt, and model — so changing any of these correctly invalidates the cache.

---

## Configuration file

All provider settings can go in `.inspectra.yml` instead of env vars:

```yaml
provider: nvidia
model: meta/llama-3.3-70b-instruct

# API keys (or use env vars)
# nvidia_api_key: nvapi-...
# openai_api_key: sk-...
# anthropic_api_key: sk-ant-...
# openrouter_api_key: sk-or-...

# Self-hosted endpoint overrides
# nvidia_base_url: http://localhost:8000/v1   # self-hosted NIM
# openai_base_url: https://internal-proxy.company.com/v1

ollama:
  host: http://localhost:11434
  timeout: 300
```

Run `inspectra init` to create a default config file.
