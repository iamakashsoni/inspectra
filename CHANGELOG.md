# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

_Changes that are merged but not yet released._

---

## [0.1.1] — 2026-05-27

### Fixed
- Fetch PR diffs via the GitHub REST API (`/repos/{owner}/{repo}/pulls/{number}`)
  instead of the web `.diff` URL, which returned 404 in GitHub Actions for many repos
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
