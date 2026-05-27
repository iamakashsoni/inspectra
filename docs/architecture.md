# Inspectra Architecture

## System Overview

```
Developer creates PR
      │
      ▼
GitHub Action triggers Inspectra
      │
      ▼
inspectra review (CLI)
      │
      ├─► Config Loader (.inspectra.yml + env vars)
      │
      ├─► Git Diff Engine
      │     ├── get_local_diff() / get_pr_diff()
      │     ├── parse_diff()        [unidiff]
      │     └── filter_files()      [skip locks, minified, binary]
      │
      ├─► Token Chunker
      │     └── chunk_diff_by_file()  [hunk-level splitting]
      │
      ├─► LLM Provider
      │     ├── OllamaProvider     (local — recommended)
      │     ├── OpenAIProvider     (cloud)
      │     ├── AnthropicProvider  (cloud)
      │     └── CachedProvider     (wraps any provider)
      │
      ├─► Review Engine
      │     ├── ChunkReviewer      (prompt → JSON → ReviewResult)
      │     ├── _merge_results()   (combine chunks per file)
      │     └── generate_pr_summary()
      │
      └─► Output
            ├── Console (Rich tables + panels)
            ├── Markdown report
            ├── SARIF report       (GitHub Code Scanning)
            └── GitHub PR comment
```

## Module Map

| Package              | Responsibility                                   |
|----------------------|--------------------------------------------------|
| `config/`            | Settings (Pydantic), YAML loader, env merging    |
| `git/`               | Diff fetching, parsing, file filtering           |
| `llm/`               | Provider abstraction + Ollama/OpenAI/Anthropic   |
| `review/`            | Prompts, reviewer, engine, severity, formatter   |
| `github/`            | Auth, PR diff fetch, comment + review posting    |
| `output/`            | Console UI, Markdown writer, SARIF exporter      |
| `utils/`             | Logger, tokenizer, chunker, disk cache           |
| `cli.py`             | Typer CLI — entry point for all commands         |

## Data Flow

```
raw diff (str)
    │
    ▼
parse_diff()
    │  dict[file_path → diff_text]
    ▼
filter_files()
    │  dict[file_path → diff_text]  (filtered)
    ▼
chunk_diff_by_file()
    │  list[DiffChunk]
    ▼
ChunkReviewer.review()  ──► LLM provider
    │  ReviewResult per chunk
    ▼
_merge_results()
    │  list[ReviewResult]  (one per file)
    ▼
Output layer
    ├── Console
    ├── Markdown
    ├── SARIF
    └── GitHub PR comment
```

## Caching Layer

```
CachedProvider
    │
    ├── cache.get(sha256(prompt))  → hit → return cached response
    │
    └── miss → inner provider.review_code(prompt)
                    │
                    └── cache.set(key, response)
```

Cache is stored in `.inspectra_cache/` (gitignored automatically).
TTL defaults to 7 days.

## LLM Provider Architecture

```python
class BaseLLMProvider(ABC):
    async def review_code(self, prompt: str) -> str: ...

OllamaProvider(BaseLLMProvider)    # http://localhost:11434
OpenAIProvider(BaseLLMProvider)    # api.openai.com
AnthropicProvider(BaseLLMProvider) # api.anthropic.com
CachedProvider(BaseLLMProvider)    # decorator over any provider
```

## Severity Pipeline

```
LLM JSON response
    │
    ▼
ReviewIssue(
    title, severity, category,
    explanation, suggested_fix,
    file_path, line_number
)
    │
    ▼
ReviewResult(
    file_path, issues[], summary
)
    │
    ▼
decide_review_event()
    ├── CRITICAL / HIGH  → REQUEST_CHANGES
    ├── MEDIUM / LOW     → COMMENT
    └── none             → APPROVE
```

## Token Budget

| Setting           | Default | Description                            |
|-------------------|---------|----------------------------------------|
| `max_tokens`      | 12 000  | Total token budget per review session  |
| `max_chunk_tokens`| 3 000   | Max tokens per single diff chunk       |

Files exceeding 2 000 diff lines are skipped entirely.
Large single-file diffs are split at `@@` hunk boundaries.

## SARIF Integration

Inspectra exports [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/)
compatible with **GitHub Code Scanning**.

```yaml
# .github/workflows/inspectra.yml
- run: inspectra review --sarif inspectra.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: inspectra.sarif
```
