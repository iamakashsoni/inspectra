"""Tests for GitHub pull request helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from inspectra.github.pull_request import get_pr_diff


def test_get_pr_diff_uses_github_api_endpoint():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "diff --git a/foo.py b/foo.py\n"

    with patch("inspectra.github.pull_request.httpx.get", return_value=mock_response) as mock_get:
        diff = get_pr_diff("ghs_testtoken", "owner/repo", 42)

    assert diff.startswith("diff --git")
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert call_args.args[0] == "https://api.github.com/repos/owner/repo/pulls/42"
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer ghs_testtoken"
    assert headers["Accept"] == "application/vnd.github.diff"


@pytest.mark.parametrize(
    ("status_code", "expected_exception", "expected_message"),
    [
        (401, PermissionError, "invalid or expired"),
        (403, PermissionError, "does not have permission"),
        (404, ValueError, "PR #7 not found"),
    ],
)
def test_get_pr_diff_maps_http_errors(status_code, expected_exception, expected_message):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = ""

    with patch("inspectra.github.pull_request.httpx.get", return_value=mock_response):
        with pytest.raises(expected_exception, match=expected_message):
            get_pr_diff("ghs_testtoken", "owner/repo", 7)
