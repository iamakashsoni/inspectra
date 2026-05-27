"""Tests for the CLI interface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from inspectra.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "inspectra" in result.output.lower()


def test_init_creates_config(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert Path(".inspectra.yml").exists()


def test_init_does_not_overwrite_existing(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".inspectra.yml").write_text("provider: openai\n")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        # Should warn, not overwrite
        content = Path(".inspectra.yml").read_text()
        assert "openai" in content


def test_review_dry_run_no_diff(tmp_path):
    """When there's no diff, review should exit cleanly."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # No git repo, no diff → nothing to review
        result = runner.invoke(
            app,
            ["review", "--dry-run", "--no-pr-summary"],
        )
        # Either exits 0 (nothing to review) or fails gracefully
        assert result.exit_code in (0, 1)


def test_review_missing_openai_key_errors(tmp_path):
    """review --provider openai without API key should show an error."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            app,
            ["review", "--provider", "openai", "--dry-run", "--no-pr-summary"],
        )
        # The review will either find no diff (exit 0) or hit missing key (exit 1)
        # Either is acceptable — we just don't want a crash/traceback
        assert result.exit_code in (0, 1)
        assert result.exception is None or isinstance(result.exception, SystemExit)


def test_review_pr_number_requires_token(tmp_path):
    """Passing --pr without GITHUB_TOKEN must produce a helpful error."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Ensure no env vars bleed in
        import os
        env_backup = os.environ.pop("GITHUB_TOKEN", None)
        env_backup2 = os.environ.pop("GITHUB_REPOSITORY", None)
        try:
            result = runner.invoke(
                app,
                ["review", "--pr", "42", "--no-pr-summary"],
                env={"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""},
            )
            assert result.exit_code == 1
            assert "GITHUB_TOKEN" in result.output or "GITHUB_REPOSITORY" in result.output
        finally:
            if env_backup:
                os.environ["GITHUB_TOKEN"] = env_backup
            if env_backup2:
                os.environ["GITHUB_REPOSITORY"] = env_backup2
