# Architecture

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
      ├─► Token Chunker (model-aware size)
      │     └── chunk_diff_by_file()  [hunk-level splitting]
      │
      ├─► Per-chunk review
      │     ├── build_file_context()       [±20 line window around changes]
      │     ├── extract_changed_signatures() [for related-changes block]
      │     ├── analyzer_registry.analyze_file() [Bandit/Semgrep/regex]
      │     ├── get_language_rules()       [Python/JS/Go antipatterns]
      │     └── ChunkReviewer.review()     [prompt → JSON → ReviewResult]
      │
      ├─► Cross-file review (second LLM pass)
      │     └── run_cross_file_review()    [caller/callee mismatch detection]
      │
      ├─► Baseline suppression
      │     └── apply_baseline()           [filter false positives]
      │
      └─► Output
            ├── Console (Rich tables + panels)
            ├── Markdown report (with GitHub suggestion blocks)
            ├── SARIF report (stable rule IDs → Code Scanning)
            └── GitHub PR comment + inline comments
```

---

## Module Map

| Package | Responsibility |
|---------|----------------|
| `config/` | Settings (Pydantic), YAML loader, env merging |
| `git/` | Diff fetching, parsing, file filtering |
| `llm/` | Provider abstraction + 5 implementations |
| `review/` | Prompts, reviewer, engine, severity, formatter, analyzers, baseline, cross-file, context builder |
| `github/` | Auth, PR diff fetch, comment + review posting |
| `output/` | Console UI, Markdown writer, SARIF exporter |
| `utils/` | Logger, tokenizer, chunker, cache, language detection, language rules |
| `cli.py` | Typer CLI — entry point for all commands |

---

## LLM Provider Architecture

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

### Key design decisions

- **`LLMRequest`/`LLMResponse` dataclasses** carry system prompt, JSON schema, temperature, max_tokens, finish_reason, and token usage — replaces the old `review_code(prompt) -> str` interface
- **Shared `OpenAICompatibleProvider` base** — OpenAI, Nvidia, and OpenRouter share the same HTTP code, just different `base_url` and default model
- **Structured JSON output via schema** — each provider uses its native mechanism (`response_format`, `tool_use`, `format=`) to guarantee valid JSON
- **Connection pooling** — each provider reuses a single `httpx.AsyncClient` across all calls
- **`finish_reason` normalization** — provider-specific values (`max_tokens`, `end_turn`, `length`) are normalized to a canonical set

---

## Review Pipeline

### Per-chunk review

1. **Chunk the diff** at hunk boundaries, respecting the model's context window
2. **Build file context** — read the working-tree file, extract a ±20-line window around each change
3. **Run deterministic analyzers** — regex (always), Bandit (Python), Semgrep (all languages)
4. **Extract related changes** — `def`/`class` signatures from other changed files
5. **Get language rules** — antipattern checklist for the file's language
6. **Build the prompt** — system prompt + rubric + few-shot + categories + language rules + PR intent + file context + related changes + analyzer findings + diff + output format
7. **Call the LLM** with schema-enforced JSON output
8. **Retry on failure** — up to 3× on JSON parse errors (with corrective prompt), up to 2× on transient network errors (timeouts, 429, 503)
9. **Parse the response** into `ReviewIssue` objects

### Cross-file review (second pass)

After all chunks are reviewed, a single LLM call receives all changed signatures across all files and looks for cross-file inconsistencies.

### Baseline suppression

Findings matching the baseline file are filtered out before output.

---

## Severity Pipeline

```
LLM JSON response
    │
    ▼
ReviewIssue(
    title, severity, category,
    explanation, suggested_fix,
    file_path, line_number, rule_id
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

---

## Caching Layer

```
CachedProvider
    │
    ├── cache.get(key)  → hit → return cached response
    │       key = sha256(user_prompt + system_prompt + temperature + max_tokens + schema + model)
    │
    └── miss → inner provider.complete(request)
                    │
                    └── cache.set(key, response)
```

Cache is stored in `.inspectra_cache/` (gitignored automatically). TTL defaults to 7 days. Cache writes are atomic (temp file + `os.replace`).

---

## Token Budget

| Setting | Default | Description |
|---------|---------|-------------|
| `max_tokens` | 12,000 | Total token budget per review session |
| `max_chunk_tokens` | 3,000 | Max tokens per diff chunk (overridden by model-aware sizing) |
| `effective_max_chunk_tokens()` | model-dependent | Uses up to half the model's context window, capped at 16k |

Files exceeding 2,000 diff lines are skipped entirely. Large single-file diffs are split at `@@` hunk boundaries.

---

## SARIF Integration

Inspectra exports [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) compatible with **GitHub Code Scanning**.

Rule IDs are stable (3-layer fallback):
1. LLM-provided `rule_id` (e.g. `SQL_INJECTION`) — normalized to uppercase
2. Canonical map (`"sql injection" → SQL_INJECTION`, `"xss" → XSS`, etc.)
3. Hash of normalized title (`sha256[:8]`) for unknown findings

This ensures the same finding produces the same rule ID across runs, so GitHub Code Scanning baselines and alert dismissal work correctly.
