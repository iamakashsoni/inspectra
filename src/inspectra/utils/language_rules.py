# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Language-specific antipattern rules for the review prompt.

For each detected language, returns a short list of high-signal things the
LLM should specifically look for. This gives the LLM language-specific
expertise without bloating the prompt for languages not in the diff.
"""

from __future__ import annotations

from inspectra.utils.language import detect_language

# Per-language rules. Each entry is a short bullet list of antipatterns
# specific to that language. Kept concise — the LLM doesn't need an
# encyclopedia, just the highest-signal reminders.
_LANGUAGE_RULES: dict[str, str] = {
    "python": """\
Python-specific things to check:
- SQL injection via f-strings or .format() in execute() calls
- pickle.loads() on untrusted input (RCE risk)
- subprocess with shell=True (shell injection)
- Bare `except:` (hides SystemExit, KeyboardInterrupt)
- Mutable default arguments (lists/dicts shared across calls)
- eval()/exec() on dynamic input
- Missing `self` parameter on methods
- asyncio: missing `await` on coroutines (silent no-op)
- asyncio: blocking I/O in async functions (defeats concurrency)
- Using == to compare to None (should be `is None`)
""",
    "javascript": """\
JavaScript-specific things to check:
- dangerouslySetInnerHTML (React) without sanitization
- eval() / new Function() with dynamic input
- innerHTML assignment with unsanitized input
- == vs === (loose equality coercion bugs)
- var instead of let/const (hoisting + scope bugs)
- Missing await on async functions (Promise instead of value)
- Process.env injection in shell commands
- Prototype pollution from Object.assign / spread on user input
- Regex DoS (catastrophic backtracking) on user-controlled patterns
""",
    "typescript": """\
TypeScript-specific things to check:
- `any` type annotations (defeats the purpose of TS)
- Non-null assertion (!) where a null check is safer
- @ts-ignore comments suppressing real type errors
- `as` type assertions that lie about the runtime type
- Missing return type annotations on public functions
- Unhandled promise rejections (no .catch or try/await)
- dangerouslySetInnerHTML (React) without sanitization
""",
    "go": """\
Go-specific things to check:
- defer in a loop (resources not released until function returns)
- goroutine leaks (no context cancellation)
- Unchecked errors (Go has no exceptions — every error must be handled)
- interface{} (now `any`) usage where a concrete type would be clearer
- Range loop variable capture (pre-Go 1.22 loop variable scope bug)
- sync.Mutex not unlocked on error paths (use defer Unlock)
- context.Context not propagated to downstream calls
""",
    "rust": """\
Rust-specific things to check:
- unwrap() / expect() on Results/Options that could realistically fail
- unsafe blocks without a safety comment
- Cloning where a reference would suffice
- .clone() in a hot loop (consider borrow or Cow)
- Blocking I/O in async code (use tokio::io instead)
- Mutex<T> where RwLock<T> would be more appropriate
""",
    "java": """\
Java-specific things to check:
- Resources not closed (use try-with-resources)
- Raw types (List instead of List<String>)
- Empty catch blocks (swallowed exceptions)
- StringBuffer where StringBuilder would suffice (no synchronization needed)
- equals() without hashCode() (breaks HashMap/HashSet)
- Public mutable fields (encapsulate with getters/setters)
""",
    "ruby": """\
Ruby-specific things to check:
- eval() / instance_eval() / class_eval() on dynamic input
- send() / public_send() with user-controlled method names
- SQL injection via string interpolation in .where()
- Missing frozen string literal magic comment
- rescue => e without re-raising when appropriate
""",
    "php": """\
PHP-specific things to check:
- SQL injection via string interpolation in query()
- eval() / assert() on dynamic input
- unserialize() on untrusted input (RCE via __wakeup/__destruct)
- $_GET/$_POST/$_REQUEST used directly without validation
- File inclusion (include/require) with user input
- exec() / shell_exec() / system() with user input
""",
    "csharp": """\
C#-specific things to check:
- async void methods (cannot be awaited, exceptions crash the process)
- .Result / .Wait() on async tasks (deadlock risk)
- Missing ConfigureAwait(false) in library code
- String concatenation in SQL commands (use parameterized queries)
- Empty catch blocks
- IDisposable not disposed (use `using`)
""",
    "c": """\
C-specific things to check:
- Buffer overflows (strcpy, strcat, sprintf — use strncpy, snprintf)
- Off-by-one errors in array indexing
- malloc without matching free (memory leak)
- Use-after-free
- Integer overflow in size calculations
- gets() (removed in C11 — use fgets)
- Format string bugs (printf(user_input) — use printf("%s", user_input))
""",
    "cpp": """\
C++-specific things to check:
- Raw pointers with manual new/delete (use smart pointers)
- Undefined behavior: signed integer overflow, null dereference, etc.
- Missing virtual destructor on base classes with virtual methods
- Iterator invalidation in loops modifying containers
- strcpy/sprintf (use strncpy/snprintf or std::string)
- RAII violations (resources not tied to object lifetime)
""",
}


def get_language_rules(file_path: str) -> str:
    """Return the language-specific rules block for a file, or empty string."""
    language = detect_language(file_path)
    if not language:
        return ""
    return _LANGUAGE_RULES.get(language, "")


def get_supported_languages() -> list[str]:
    """Return the list of languages with specific rules."""
    return sorted(_LANGUAGE_RULES.keys())
