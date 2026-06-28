"""Tests for the analyzer plugin system (Phase 2 #21/#22)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer
from inspectra.review.analyzers.regex_analyzer import RegexAnalyzer
from inspectra.review.analyzers.registry import AnalyzerRegistry, build_default_registry
from inspectra.utils.language import detect_language


# ── RegexAnalyzer ────────────────────────────────────────────────────────────

def test_regex_detects_eval_in_python():
    analyzer = RegexAnalyzer()
    content = "result = eval(user_input)\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/EVAL" in rule_ids


def test_regex_detects_pickle_loads():
    analyzer = RegexAnalyzer()
    content = "import pickle\ndata = pickle.loads(unsafe_data)\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/PICKLE_LOADS" in rule_ids


def test_regex_detects_subprocess_shell_true():
    analyzer = RegexAnalyzer()
    content = "import subprocess\nsubprocess.run(cmd, shell=True)\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/SUBPROCESS_SHELL_TRUE" in rule_ids


def test_regex_detects_sql_string_format():
    analyzer = RegexAnalyzer()
    content = "cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/SQL_STRING_FORMAT" in rule_ids
    sql_finding = next(f for f in findings if f.rule_id == "REGEX/SQL_STRING_FORMAT")
    assert sql_finding.severity == "critical"
    assert sql_finding.category == "Security"


def test_regex_detects_hardcoded_secret():
    analyzer = RegexAnalyzer()
    content = 'api_key = "sk-1234567890abcdef"\n'
    findings = analyzer.analyze("config.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/HARDCODED_SECRET" in rule_ids


def test_regex_detects_bare_except():
    analyzer = RegexAnalyzer()
    content = "try:\n    do_thing()\nexcept:\n    pass\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/BARE_EXCEPT" in rule_ids


def test_regex_detects_mutable_default_arg():
    analyzer = RegexAnalyzer()
    content = "def append_to(item, target=[]):\n    target.append(item)\n"
    findings = analyzer.analyze("test.py", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/MUTABLE_DEFAULT_ARG" in rule_ids


def test_regex_detects_dangerously_set_inner_html():
    analyzer = RegexAnalyzer()
    content = '<div dangerouslySetInnerHTML={{__html: userInput}} />\n'
    findings = analyzer.analyze("component.jsx", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/DANGEROUSLY_SET_INNER_HTML" in rule_ids


def test_regex_respects_language_filter():
    """eval() pattern should only fire on Python/JS/TS, not Go."""
    analyzer = RegexAnalyzer()
    content = "result := eval(input)\n"  # Go-like syntax
    # Go file — eval pattern shouldn't fire
    findings = analyzer.analyze("test.go", content, "")
    rule_ids = [f.rule_id for f in findings]
    assert "REGEX/EVAL" not in rule_ids


def test_regex_no_false_positive_on_normal_code():
    analyzer = RegexAnalyzer()
    content = (
        "def calculate(x, y):\n"
        "    return x + y\n"
        "\n"
        "result = calculate(1, 2)\n"
    )
    findings = analyzer.analyze("clean.py", content, "")
    assert len(findings) == 0, f"Expected no findings on clean code, got {[f.rule_id for f in findings]}"


def test_regex_finding_has_line_number():
    analyzer = RegexAnalyzer()
    content = "x = 1\neval(bad)\n"
    findings = analyzer.analyze("test.py", content, "")
    eval_finding = next(f for f in findings if f.rule_id == "REGEX/EVAL")
    assert eval_finding.line_number == 2


def test_regex_finding_has_suggested_fix():
    analyzer = RegexAnalyzer()
    content = "eval(user_input)\n"
    findings = analyzer.analyze("test.py", content, "")
    eval_finding = next(f for f in findings if f.rule_id == "REGEX/EVAL")
    assert eval_finding.suggested_fix != ""
    assert "ast.literal_eval" in eval_finding.suggested_fix or "safer" in eval_finding.suggested_fix.lower()


# ── AnalyzerRegistry ─────────────────────────────────────────────────────────

class _FakePythonAnalyzer(BaseAnalyzer):
    name = "fake_python"
    supported_languages = ["python"]

    def analyze(self, file_path, full_content, diff_text):
        return [AnalyzerFinding(
            rule_id="FAKE/PY001", severity="low", category="Bugs",
            title="Fake finding", explanation="test",
            file_path=file_path, line_number=1, analyzer_name=self.name,
        )]


class _FakeAllAnalyzer(BaseAnalyzer):
    name = "fake_all"
    supported_languages = []  # all languages

    def analyze(self, file_path, full_content, diff_text):
        return [AnalyzerFinding(
            rule_id="FAKE/ALL001", severity="info", category="General",
            title="Fake all-language finding", explanation="test",
            file_path=file_path, line_number=1, analyzer_name=self.name,
        )]


def test_registry_routes_by_language():
    reg = AnalyzerRegistry()
    reg.register(_FakePythonAnalyzer())
    reg.register(_FakeAllAnalyzer())

    # Python file: both analyzers apply
    py_analyzers = reg.for_language("python")
    assert len(py_analyzers) == 2

    # Go file: only the all-language analyzer applies
    go_analyzers = reg.for_language("go")
    assert len(go_analyzers) == 1
    assert go_analyzers[0].name == "fake_all"


def test_registry_analyze_file_combines_findings():
    reg = AnalyzerRegistry()
    reg.register(_FakePythonAnalyzer())
    reg.register(_FakeAllAnalyzer())

    findings = reg.analyze_file("test.py", "some content", "")
    rule_ids = [f.rule_id for f in findings]
    assert "FAKE/PY001" in rule_ids
    assert "FAKE/ALL001" in rule_ids


def test_registry_analyzer_crash_doesnt_block_others():
    """If one analyzer crashes, others should still run."""
    class _CrashingAnalyzer(BaseAnalyzer):
        name = "crasher"
        supported_languages = []

        def analyze(self, file_path, full_content, diff_text):
            raise RuntimeError("boom")

    reg = AnalyzerRegistry()
    reg.register(_CrashingAnalyzer())
    reg.register(_FakeAllAnalyzer())

    findings = reg.analyze_file("test.py", "content", "")
    # The crasher produced nothing, but the all-language analyzer still ran
    assert len(findings) == 1
    assert findings[0].rule_id == "FAKE/ALL001"


def test_build_default_registry_includes_regex():
    """The default registry should always include the regex analyzer."""
    reg = build_default_registry()
    names = [a.name for a in reg.all()]
    assert "regex" in names


def test_build_default_registry_skips_missing_bandit():
    """Bandit analyzer should only be in the registry if bandit is installed."""
    reg = build_default_registry()
    names = [a.name for a in reg.all()]
    # Bandit may or may not be installed in the test env — either is fine
    # The point is: no crash if it's missing
    assert "regex" in names  # regex is always there


# ── BanditAnalyzer (only runs if bandit is installed) ────────────────────────

def test_bandit_is_available_check():
    """is_available() should return True/False without crashing."""
    from inspectra.review.analyzers.bandit_analyzer import BanditAnalyzer
    result = BanditAnalyzer.is_available()
    assert isinstance(result, bool)


def test_bandit_skips_when_not_installed():
    """If bandit isn't installed, analyze() returns empty list (no crash)."""
    from inspectra.review.analyzers.bandit_analyzer import BanditAnalyzer
    with patch("inspectra.review.analyzers.bandit_analyzer.BanditAnalyzer.is_available", return_value=False):
        analyzer = BanditAnalyzer()
        findings = analyzer.analyze("test.py", "eval(x)", "")
        assert findings == []


# ── SemgrepAnalyzer (only runs if semgrep is installed) ──────────────────────

def test_semgrep_is_available_check():
    from inspectra.review.analyzers.semgrep_analyzer import SemgrepAnalyzer
    result = SemgrepAnalyzer.is_available()
    assert isinstance(result, bool)
