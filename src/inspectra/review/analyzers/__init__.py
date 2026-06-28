"""Analyzer plugin system for Inspectra.

Deterministic analyzers (Bandit, Semgrep, regex patterns) run BEFORE the LLM
and feed their findings into the prompt. The LLM then confirms, expands, or
dismisses each finding — best of both worlds:
- Deterministic tools catch known patterns (eval, hardcoded secrets, CVEs)
- LLM enriches with semantic context ("this eval() is actually safe because...")
- LLM catches new patterns the analyzers don't know about

Adding a new analyzer:
1. Subclass BaseAnalyzer
2. Implement `analyze(file_path, full_content, diff_text) -> list[AnalyzerFinding]`
3. Register it in the registry (or via entry points in pyproject.toml)
"""

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer
from inspectra.review.analyzers.registry import AnalyzerRegistry

__all__ = ["AnalyzerFinding", "BaseAnalyzer", "AnalyzerRegistry"]
