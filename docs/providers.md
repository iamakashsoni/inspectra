# LLM Provider Setup

## Ollama (Recommended — Local, Free, Private)

### Why Ollama?

| Advantage           | Detail                                              |
|---------------------|-----------------------------------------------------|
| Zero cost           | No API fees; runs on your hardware                  |
| Privacy             | Code never leaves your network                      |
| Offline             | Works in air-gapped environments                    |
| No rate limits      | Review as many PRs as you want                      |
| Customisable        | Swap or fine-tune models freely                     |

### Install

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Start the server

```bash
ollama serve
```

### Pull a model

```bash
# Recommended default
ollama pull qwen2.5-coder:14b

# Lightweight option
ollama pull codellama:13b

# Enterprise — needs ~20 GB RAM
ollama pull qwen2.5-coder:32b
```

### Verify

```bash
inspectra models
```

### Configuration

```yaml
# .inspectra.yml
provider: ollama
model: qwen2.5-coder:14b
ollama:
  host: http://localhost:11434
  timeout: 300
```

### Self-hosted GitHub Runner

To use Ollama in CI, your runner machine needs:

- Python 3.11+
- Ollama installed and running
- The model already pulled (to avoid download on every run)
- ≥16 GB RAM for 14B models; ≥32 GB for 32B models

```yaml
# .github/workflows/inspectra.yml
jobs:
  inspectra:
    runs-on: self-hosted  # <-- your Ollama machine
```

---

## OpenAI

### Setup

```bash
export OPENAI_API_KEY=sk-...
```

### Recommended models

| Model          | Speed   | Quality  | Cost  |
|----------------|---------|----------|-------|
| `gpt-4o-mini`  | Fast    | Good     | Low   |
| `gpt-4o`       | Medium  | Excellent| Medium|

### Configuration

```yaml
provider: openai
model: gpt-4o-mini
```

### GitHub Actions

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## Anthropic Claude

### Setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Recommended models

| Model                        | Notes                |
|------------------------------|----------------------|
| `claude-sonnet-4-20250514`   | Best balance         |
| `claude-haiku-4-5-20251001`  | Fast and cheap       |

### Configuration

```yaml
provider: anthropic
model: claude-sonnet-4-20250514
```

### GitHub Actions

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

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
