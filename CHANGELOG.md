# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — Unreleased

### Added — Phase 2: Deeper code understanding

- **File context builder**: the LLM now sees ±20 lines around each change, not just the diff. Reads the working-tree file, finds changed ranges via `unidiff`, and extracts a context window truncated to a 2000-token budget.
- **PR intent**: the prompt includes the PR title and branch info (auto-extracted, or set via `--pr-intent`). Lets the LLM calibrate its review (lenient on refactors, strict on security changes).
- **Related changes block**: when reviewing file A, the prompt includes `def`/`class`/`func` signatures from files B, C, D changed in the same PR. Cross-file awareness without sending full content.
- **Deterministic analyzer plugin system**: three analyzers feed findings into the LLM prompt for confirmation/enrichment:
  - `RegexAnalyzer` (built-in, no deps): catches `eval()`, `pickle.loads()`, `shell=True`, SQL injection, hardcoded secrets, bare `except:`, mutable default args, `dangerouslySetInnerHTML`
  - `BanditAnalyzer` (optional, `pip install bandit`): full Bandit rule set
  - `SemgrepAnalyzer` (optional, `pip install semgrep`): full Semgrep rule registry
- **Language-specific prompt rules**: 11 languages get curated antipattern checklists (Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP, C#, C, C++)
- **Two-pass cross-file review**: after the per-file pass, a second LLM call looks at all changed signatures across all files for caller/callee mismatches
- **Baseline suppression**: `.inspectra-baseline.json` + `inspectra suppress` / `inspectra baseline-show` commands. Record false positives with optional file/line scoping and expiry dates
- **Model-aware chunk sizing**: chunks use the model's full context window (capped at 16k). 6× fewer LLM calls on large PRs with cloud providers
- **Nvidia NIM provider**: `--provider nvidia` with self-hosted NIM support (`--base-url http://localhost:8000/v1`) for air-gapped reviews
- **OpenRouter provider**: `--provider openrouter` — one API key, access to dozens of model providers

### Changed — Phase 1 audit fixes

- **Cache key now includes temperature, system_prompt, max_tokens, and schema presence** — previously changing temperature returned a stale cached response
- **`_looks_like_code()` no longer treats prose starting with `-` or `+` as code** — was wrongly rendering "- Remove the import" as a GitHub suggestion block
- **Few-shot example uses a placeholder file_path** — LLMs were copying `auth/service.py` from the example into findings for other files
- **`post_inline_comments()` fetches commit ONCE** — was calling `repo.get_commit()` per issue (N+1 API calls)
- **Network errors now retried** (timeouts, 429, 503) with exponential backoff — previously only JSON parse errors retried
- **`asyncio.gather()` uses `return_exceptions=True`** — one chunk failure no longer loses all results
- **Shared `httpx.AsyncClient` per provider** (connection pooling) — was creating a new client per request
- **Cache writes are atomic** (temp file + `os.replace`) — crash mid-write no longer leaves corrupted entries
- **`--base-url` for Ollama preserves timeout** — was replacing the entire OllamaConfig
- **System prompt includes prompt-injection defense** — malicious diff content can't override instructions
- **`finish_reason` normalized across providers** — Anthropic's `max_tokens` now maps to `length` so truncation detection works
- **Structured JSON output via schema** on all providers — eliminates ~30% of parse failures
- **Retry on JSON parse failure** (3× with corrective prompt)
- **GitHub suggestion blocks** for code-like fixes — one-click "Apply suggestion" button in PR UI
- **Inline PR comments wired up** (was dead code) — `head_sha` added to PR metadata, old inline comments cleaned up on re-run
- **Configurable concurrency** with per-provider defaults (was hardcoded at 3)
- **Stable SARIF rule IDs** (canonical map + hash fallback) — GitHub Code Scanning baselines work correctly
- **All 4 GitHub Actions workflows fixed**: concurrency groups, path filters, fetch-depth, SARIF upload, fail-open, timeouts, dogfooding step

### Removed

- `AUDIT.md`, `CHANGES.md`, `PHASE2.md` — internal development artifacts, not shipped

---

## [0.1.1] — 2026-05-27

### Fixed
- Fetch PR diffs via the GitHub REST API (`/repos/{owner}/{repo}/pulls/{number}`) instead of the web `.diff` URL, which returned 404 in GitHub Actions for many repos
- Add clear errors for invalid tokens (401), missing permissions (403), and missing PRs (404)

---

## [0.1.0] — 2025-01-01

### Added
- Initial release
- Git diff engine — parses and filters changed hunks only
- LLM provider system — Ollama (local), OpenAI, Anthropic
- Caching layer — disk-based SHA-256 keyed response cache
- Review engine — chunked diff review with per-file result merging
- Severity system — Critical / High / Medium / Low / Info
- PR summary generation — AI-generated PR-level overview
- GitHub integration — PR diff fetch, comment posting, review submission
- Console output — Rich tables, severity-coloured panels
- Markdown report output
- SARIF export — SARIF 2.1.0, compatible with GitHub Code Scanning
- CLI commands — `review`, `init`, `models`, `version`, `cache-clear`
- GitHub Actions workflows — Ollama (self-hosted), OpenAI (hosted), CI, PyPI publish
- Pre-commit hook support

[Unreleased]: https://github.com/iamakashsoni/inspectra/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/iamakashsoni/inspectra/releases/tag/v0.1.1
[0.1.0]: https://github.com/iamakashsoni/inspectra/releases/tag/v0.1.0
