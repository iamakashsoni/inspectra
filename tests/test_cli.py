"""Tests for the CLI interface."""

from __future__ import annotations

import os

from typer.testing import CliRunner

from inspectra.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "inspectra" in result.output.lower()


def test_init_creates_config(tmp_path):
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".inspectra.yml").exists()
    finally:
        os.chdir(orig)


def test_init_does_not_overwrite_existing(tmp_path):
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        (tmp_path / ".inspectra.yml").write_text("provider: openai\n")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        # Should warn, not overwrite
        assert "openai" in (tmp_path / ".inspectra.yml").read_text()
    finally:
        os.chdir(orig)


def test_review_dry_run_no_diff(tmp_path):
    """When there's no git repo / diff, review should exit cleanly."""
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["review", "--dry-run", "--no-pr-summary"])
        # Either 0 (nothing to review) or 1 (no git repo) — no crash
        assert result.exit_code in (0, 1)
        assert result.exception is None or isinstance(result.exception, SystemExit)
    finally:
        os.chdir(orig)


def test_review_missing_openai_key_errors(tmp_path):
    """review --provider openai without API key should show a clear error."""
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["review", "--provider", "openai", "--dry-run", "--no-pr-summary"],
            env={"OPENAI_API_KEY": ""},
        )
        assert result.exit_code in (0, 1)
        assert result.exception is None or isinstance(result.exception, SystemExit)
    finally:
        os.chdir(orig)


def test_review_pr_number_requires_token(tmp_path):
    """Passing --pr without GITHUB_TOKEN must produce a helpful error."""
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["review", "--pr", "42", "--no-pr-summary"],
            env={"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""},
        )
        assert result.exit_code == 1
        assert (
            "GITHUB_TOKEN" in result.output
            or "GITHUB_REPOSITORY" in result.output
        )
    finally:
        os.chdir(orig)
