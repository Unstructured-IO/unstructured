"""Hermetic telemetry tests: env is set to opt-out before importing unstructured.

This module must set DO_NOT_TRACK (or equivalent) before any import of unstructured
so that init_telemetry() runs with opt-out at import time and no real network/subprocess
occurs. Tests then use monkeypatch and mocks to assert behavior.
"""

from __future__ import annotations

# Set opt-out before any unstructured import so package init does not run telemetry.
import os

os.environ["DO_NOT_TRACK"] = "1"
os.environ.pop("UNSTRUCTURED_TELEMETRY_ENABLED", None)
os.environ.pop("SCARF_NO_ANALYTICS", None)

import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from unstructured import utils


@pytest.fixture
def telemetry_mocks(monkeypatch):
    """Clear telemetry env and patch requests.get + subprocess.check_output.

    Returns (mock_get, mock_subprocess). Use for both send and no-send tests so
    we can assert network and subprocess side effects.
    """
    monkeypatch.delenv("UNSTRUCTURED_TELEMETRY_ENABLED", raising=False)
    monkeypatch.delenv("SCARF_NO_ANALYTICS", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    mock_get = Mock()
    mock_subprocess = Mock()
    monkeypatch.setattr("unstructured.utils.requests.get", mock_get)
    monkeypatch.setattr("unstructured.utils.subprocess.check_output", mock_subprocess)
    return mock_get, mock_subprocess


def _apply_telemetry_env(monkeypatch, env_overrides):
    """Set env vars from dict; keys are env var names, values are str or None (delenv)."""
    for key, value in env_overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


class DescribeScarfAnalytics:
    """Tests for scarf_analytics (telemetry off by default, opt-in only)."""

    def it_telemetry_opt_out_any_non_empty_for_both_vars(self, monkeypatch):
        """Contract: DO_NOT_TRACK and SCARF_NO_ANALYTICS both opt out on any non-empty value."""
        monkeypatch.delenv("DO_NOT_TRACK", raising=False)
        monkeypatch.delenv("SCARF_NO_ANALYTICS", raising=False)
        assert utils._telemetry_opt_out() is False
        monkeypatch.setenv("DO_NOT_TRACK", "yes")
        assert utils._telemetry_opt_out() is True
        monkeypatch.delenv("DO_NOT_TRACK", raising=False)
        monkeypatch.setenv("SCARF_NO_ANALYTICS", "on")
        assert utils._telemetry_opt_out() is True

    def it_telemetry_opt_in_only_true_or_1(self, monkeypatch):
        """Contract: only UNSTRUCTURED_TELEMETRY_ENABLED in ('true','1') opts in."""
        monkeypatch.delenv("UNSTRUCTURED_TELEMETRY_ENABLED", raising=False)
        assert utils._telemetry_opt_in() is False
        for val in ("true", "1", "True", "TRUE"):
            monkeypatch.setenv("UNSTRUCTURED_TELEMETRY_ENABLED", val)
            assert utils._telemetry_opt_in() is True
        for val in ("false", "0", "yes", ""):
            monkeypatch.setenv("UNSTRUCTURED_TELEMETRY_ENABLED", val)
            assert utils._telemetry_opt_in() is False

    @pytest.mark.parametrize(
        "env_overrides",
        [
            {},
            {"DO_NOT_TRACK": "true"},
            {"DO_NOT_TRACK": "1"},
            {"DO_NOT_TRACK": "TRUE"},
            {"DO_NOT_TRACK": "false"},
            {"DO_NOT_TRACK": "0"},
            {"SCARF_NO_ANALYTICS": "true"},
            {"SCARF_NO_ANALYTICS": "yes"},
            {"SCARF_NO_ANALYTICS": "on"},
            {"SCARF_NO_ANALYTICS": "1"},
            {"SCARF_NO_ANALYTICS": "TRUE"},
            {"SCARF_NO_ANALYTICS": "false"},
            {"SCARF_NO_ANALYTICS": "0"},
            {"SCARF_NO_ANALYTICS": "  true  "},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "false"},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "0"},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "yes"},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "FALSE"},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "true", "DO_NOT_TRACK": "true"},
            {"UNSTRUCTURED_TELEMETRY_ENABLED": "true", "SCARF_NO_ANALYTICS": "on"},
        ],
        ids=[
            "default_no_opt_in",
            "DO_NOT_TRACK=true",
            "DO_NOT_TRACK=1",
            "DO_NOT_TRACK=TRUE",
            "DO_NOT_TRACK=false",
            "DO_NOT_TRACK=0",
            "SCARF_NO_ANALYTICS=true",
            "SCARF_NO_ANALYTICS=yes",
            "SCARF_NO_ANALYTICS=on",
            "SCARF_NO_ANALYTICS=1",
            "SCARF_NO_ANALYTICS=TRUE",
            "SCARF_NO_ANALYTICS=false",
            "SCARF_NO_ANALYTICS=0",
            "SCARF_NO_ANALYTICS=whitespace",
            "opt_in=false",
            "opt_in=0",
            "opt_in=yes",
            "opt_in=FALSE",
            "opt_in_true_but_DO_NOT_TRACK",
            "opt_in_true_but_SCARF_NO_ANALYTICS",
        ],
    )
    def it_does_not_send_telemetry_when_disabled_or_opted_out(
        self, monkeypatch, telemetry_mocks, env_overrides
    ):
        """No network or subprocess when telemetry disabled or opt-out set."""
        mock_get, mock_subprocess = telemetry_mocks
        _apply_telemetry_env(monkeypatch, env_overrides)
        utils.scarf_analytics()
        mock_get.assert_not_called()
        mock_subprocess.assert_not_called()

    @pytest.mark.parametrize("opt_in_value", ["true", "True", "TRUE", "1"])
    def it_sends_telemetry_when_opt_in_is_set(self, monkeypatch, telemetry_mocks, opt_in_value):
        mock_get, mock_subprocess = telemetry_mocks
        _apply_telemetry_env(monkeypatch, {"UNSTRUCTURED_TELEMETRY_ENABLED": opt_in_value})
        utils.scarf_analytics()
        mock_get.assert_called_once()
        mock_subprocess.assert_called_once_with(["nvidia-smi"], stderr=subprocess.DEVNULL)
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://packages.unstructured.io/python-telemetry"
        params = call_args[1]["params"]
        assert set(params.keys()) == {"version", "platform", "python", "arch", "gpu", "dev"}
        assert call_args[1]["timeout"] == 10

    @pytest.mark.parametrize(
        ("version_val", "expected_dev"),
        [("1.2.3.dev0", "true"), ("1.2.3", "false")],
        ids=["dev_version", "release_version"],
    )
    def it_sends_telemetry_with_correct_dev_param(
        self, monkeypatch, telemetry_mocks, version_val, expected_dev
    ):
        mock_get, mock_subprocess = telemetry_mocks
        _apply_telemetry_env(monkeypatch, {"UNSTRUCTURED_TELEMETRY_ENABLED": "true"})
        monkeypatch.setattr("unstructured.utils.__version__", version_val)
        utils.scarf_analytics()
        mock_get.assert_called_once()
        mock_subprocess.assert_called_once()
        params = mock_get.call_args[1]["params"]
        assert params["dev"] == expected_dev
        assert params["version"] == version_val
        assert params["platform"] == platform.system()
        assert params["arch"] == platform.machine()
        assert mock_get.call_args[1]["timeout"] == 10

    def it_handles_requests_exception_gracefully(self, monkeypatch, telemetry_mocks):
        mock_get, mock_subprocess = telemetry_mocks
        mock_get.side_effect = requests.RequestException("network error")
        _apply_telemetry_env(monkeypatch, {"UNSTRUCTURED_TELEMETRY_ENABLED": "true"})
        utils.scarf_analytics()  # does not raise
        mock_get.assert_called_once()
        mock_subprocess.assert_called_once()
        assert mock_get.call_args[0][0] == "https://packages.unstructured.io/python-telemetry"
        assert "version" in mock_get.call_args[1]["params"]

    @pytest.mark.parametrize(
        "exc",
        [
            OSError(),
            PermissionError("nvidia-smi denied"),
            subprocess.CalledProcessError(returncode=1, cmd=["nvidia-smi"]),
        ],
        ids=["OSError", "PermissionError", "CalledProcessError"],
    )
    def it_handles_nvidia_smi_failure_gracefully(self, monkeypatch, telemetry_mocks, exc):
        """nvidia-smi probe failures must not propagate; telemetry still sends with gpu=False."""
        mock_get, mock_subprocess = telemetry_mocks
        mock_subprocess.side_effect = exc
        _apply_telemetry_env(monkeypatch, {"UNSTRUCTURED_TELEMETRY_ENABLED": "true"})
        utils.scarf_analytics()  # does not raise
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["params"]["gpu"] == "False"
        mock_subprocess.assert_called_once_with(["nvidia-smi"], stderr=subprocess.DEVNULL)

    def it_import_unstructured_succeeds_with_opt_out(self):
        """Import path with opt-out env does not crash (integration-style)."""
        project_root = Path(__file__).resolve().parent.parent
        env = {k: v for k, v in os.environ.items() if k != "UNSTRUCTURED_TELEMETRY_ENABLED"}
        env.update(
            {
                "DO_NOT_TRACK": "1",
                "SCARF_NO_ANALYTICS": "1",
                "UNSTRUCTURED_TELEMETRY_ENABLED": "",
                "PYTHONPATH": str(project_root),
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", "import unstructured; print('ok')"],
            env=env,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert "ok" in result.stdout

    def it_import_unstructured_runs_telemetry_once_when_opt_in(self):
        """Import path with opt-in runs init_telemetry exactly once (patch then import)."""
        project_root = Path(__file__).resolve().parent.parent
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("DO_NOT_TRACK", "SCARF_NO_ANALYTICS", "UNSTRUCTURED_TELEMETRY_ENABLED")
        }
        env.update(
            {
                "UNSTRUCTURED_TELEMETRY_ENABLED": "true",
                "PYTHONPATH": str(project_root),
            }
        )
        script = """
from unittest.mock import Mock, patch
m_get = Mock()
m_subprocess = Mock()
with patch('requests.get', m_get), patch('subprocess.check_output', m_subprocess):
    import unstructured
exit(0 if (m_get.call_count == 1 and m_subprocess.call_count == 1) else 1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            "Import with opt-in should run telemetry exactly once (requests.get and "
            "subprocess.check_output each called once). "
            f"stderr={result.stderr!r} stdout={result.stdout!r}"
        )
