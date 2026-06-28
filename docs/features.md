# Features

Inspectra goes beyond syntax checking — it understands the code's functionality and provides precise, actionable suggestions.

---

## File context

The LLM sees ±20 lines around each change, not just the diff. This lets it understand the function's purpose and surrounding patterns.

**How it works:**
1. Reads the working-tree version of each changed file
2. Finds the changed line ranges via `unidiff`
3. Extracts a ±20-line window around each change
4. Truncates to a 2000-token budget, preserving the most relevant context
5. Includes the context in the prompt as "Full file content (for context — review the diff, not this)"

**Why it matters:** A diff alone tells you what changed but not what the surrounding code does. With file context, the LLM can see that a new `eval()` call is in a security-sensitive function, or that a missing `await` will silently drop a coroutine.

---

## PR intent

The LLM knows whether it's reviewing a security fix, a refactor, or a new feature — calibrating its review accordingly.

**How it works:**
- Auto-extracted from the PR title and branch info when `--pr` is set
- Override with `--pr-intent "Add user lookup endpoint for /api/users"`
- Included in the prompt as a "PR Intent" block

**Why it matters:** A security fix should be reviewed strictly; a refactor should be lenient on style; a new feature should focus on completeness. The PR intent tells the LLM which lens to use.

---

## Deterministic analyzers

Built-in regex analyzer (always available, no deps) plus optional Bandit and Semgrep wrappers. Findings are fed INTO the LLM prompt for confirmation/enrichment — best of both worlds.

| Analyzer | Languages | Install | What it catches |
|----------|-----------|---------|-----------------|
| Regex (built-in) | All | — | `eval()`, `pickle.loads()`, `shell=True`, SQL injection, hardcoded secrets, bare `except:`, mutable default args, `dangerouslySetInnerHTML` |
| Bandit | Python | `pip install bandit` | Full Bandit rule set (B101-B999) |
| Semgrep | All | `pip install semgrep` | Full Semgrep rule registry |

**How it works:**
1. Each analyzer runs on the full file content before the LLM call
2. Findings are listed in the prompt as "Deterministic analyzer findings (already detected — verify, expand, or dismiss)"
3. The LLM is instructed to:
   - **Confirm** findings it agrees with (include in response with the same `rule_id`)
   - **Dismiss** false positives (omit and add "FP:" note in summary)
   - **Enrich** with additional context the analyzers can't provide

**Why it matters:** Deterministic tools catch known patterns (CVEs, `eval`, hardcoded secrets) reliably. The LLM enriches with semantic context ("this `eval()` is actually safe because the input is a compile-time constant"). Together they catch more than either could alone.

**Disabling:** Use `--no-analyzers` to skip the analyzer pass (faster, but less coverage).

---

## Cross-file review

After the per-file pass, a second LLM call looks at all changed signatures across all files for caller/callee mismatches.

**How it works:**
1. After all per-file reviews complete, `extract_changed_signatures()` pulls `def`/`class`/`func`/`fn` declarations from every file's diff
2. A single LLM call receives all changed signatures and looks for:
   - Signature mismatches (caller updated, callee not — or vice versa)
   - Type mismatches between caller and callee
   - Missing error handling at call sites
   - Dead code (function deleted but still called elsewhere)
3. Cross-file issues are tagged with `rule_id: CROSS_FILE_SIGNATURE_MISMATCH`

**Why it matters:** Each file is reviewed in isolation in the first pass — the LLM can't see that you changed a function signature in `auth/service.py` but forgot to update the caller in `api/routes.py`. The cross-file pass catches exactly these bugs.

**Disabling:** Use `--no-cross-file` to skip (only relevant for single-file PRs).

---

## Language-specific rules

11 languages get curated antipattern checklists in the prompt.

**Supported languages:** Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP, C#, C, C++

**How it works:**
- `get_language_rules(file_path)` returns a concise block of language-specific antipatterns
- Only included when the language is detected — no prompt bloat for languages not in the diff
- Example for Python:
  ```
  Python-specific things to check:
  - SQL injection via f-strings or .format() in execute() calls
  - pickle.loads() on untrusted input (RCE risk)
  - subprocess with shell=True (shell injection)
  - Bare `except:` (hides SystemExit, KeyboardInterrupt)
  - Mutable default arguments (lists/dicts shared across calls)
  ```

**Why it matters:** The LLM doesn't need an encyclopedia, just the highest-signal reminders for the language it's reviewing. In Go, `defer` in a loop is a bug; in Python, mutable default args are a bug — the rules block tells the LLM exactly what to look for.

**Disabling:** Use `--no-language-rules` to skip.

---

## Baseline suppression

Record false positives so they're never reported again.

**How it works:**
1. Create a `.inspectra-baseline.json` file with suppression rules:
   ```json
   {
     "version": 1,
     "suppressions": [
       {
         "rule_id": "SQL_INJECTION",
         "file_path": "auth/legacy.py",
         "reason": "Legacy admin panel, deprecated Q3 2026",
         "expires": "2026-09-30"
       }
     ]
   }
   ```
2. Pass `--baseline .inspectra-baseline.json` during review
3. Findings matching a suppression are filtered out before output

**Matching logic:**
- `rule_id` match (case-insensitive) — required
- `file_path` match — optional, scopes to one file
- `line_number` match — optional, scopes to one line
- `expires` date — optional, suppression ignored after this date

**CLI commands:**
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

**Why it matters:** Without baseline suppression, every Inspectra run re-reports the same false positives. Developers get alert fatigue and start ignoring all findings. Suppression lets you teach Inspectra your codebase's known-acceptable patterns.

---

## Model-aware chunk sizing

Chunks use the model's full context window (capped at 16k).

**How it works:**
- `effective_max_chunk_tokens()` looks up the model's context window
- Uses up to half the context window (leaving room for prompt + response)
- Capped at 16k for safety
- Falls back to `max_chunk_tokens` setting (default 3000) if model is unknown

| Model | Context window | Chunk size |
|-------|---------------|------------|
| `gpt-4o-mini` | 128k | 16k |
| `claude-sonnet-4` | 200k | 16k |
| `qwen2.5-coder:14b` | 32k | 16k |
| Unknown model | — | 3k (fallback) |

**Why it matters:** A 30-file PR on `gpt-4o-mini` now makes ~5 LLM calls instead of ~30 — 6× fewer calls, 6× less latency, 6× lower cost on cloud providers.

---

## Structured JSON output

All providers use schema-enforced JSON output.

| Provider | Mechanism |
|----------|-----------|
| OpenAI / Nvidia / OpenRouter | `response_format: {type: "json_schema", json_schema: {...}}` |
| Anthropic | Tool calling with `tool_choice: {type: "tool", name: "submit_review"}` |
| Ollama | `format: <json_schema>` on `/api/chat` |

**Why it matters:** Eliminates ~30% of parse failures (LLMs wrapping JSON in markdown fences, adding trailing commentary, or truncating mid-string). When parsing still fails, Inspectra retries up to 3× with a corrective prompt showing the error.

---

## GitHub suggestion blocks

Code-like suggested fixes render as GitHub `suggestion` fenced blocks — one-click "Apply suggestion" buttons in the PR UI.

**How it works:**
- `_looks_like_code()` detects if the suggested fix is code (multi-line, or starts with `def`/`import`/etc.)
- Code fixes render as:
  <pre>```suggestion
  cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
  ```</pre>
- Prose fixes render inline as `**Suggested fix:** Remove the import.`

**Why it matters:** Developers can fix trivial issues without leaving the PR — one click applies the suggestion directly to the code.

---

## Inline PR comments

Findings with a line number are posted as inline review comments at the exact line, not just in the summary comment.

**How it works:**
- `post_inline_comments()` anchors each comment to the PR head commit
- Comments are stamped with `<!-- inspectra:inline -->` for cleanup on re-runs
- `delete_previous_inspectra_comments()` removes both summary and inline comments before posting new ones
- Only MEDIUM+ severity findings are posted inline (configurable)

**Why it matters:** This is how developers expect code review tools to behave (CodeRabbit, Greptile, CodeQL all do this). Inline comments at the exact line are far more actionable than a single PR-level comment.
