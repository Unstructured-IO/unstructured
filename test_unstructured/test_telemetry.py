"""Hermetic tests for the default-on library-load telemetry ping.

This module sets an opt-out before importing unstructured so the package initializer cannot
perform real network or subprocess work. Individual tests clear that opt-out and mock the
telemetry side effects before exercising the behavior under test.
"""

from __future__ import annotations

import os

# Set an opt-out before importing unstructured so package initialization is hermetic.
os.environ["DO_NOT_TRACK"] = "1"
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
    """Clear opt-outs and patch telemetry's network and GPU-probe side effects."""
    monkeypatch.delenv("SCARF_NO_ANALYTICS", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    mock_get = Mock()
    mock_subprocess = Mock()
    monkeypatch.setattr("unstructured.utils.requests.get", mock_get)
    monkeypatch.setattr("unstructured.utils.subprocess.check_output", mock_subprocess)
    return mock_get, mock_subprocess


def _apply_telemetry_env(monkeypatch, env_overrides):
    """Set env vars from a mapping whose values are strings or None to remove a variable."""
    for key, value in env_overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


class DescribeScarfAnalytics:
    """Tests for the default-on library-load analytics ping."""

    def it_sends_telemetry_by_default(self, telemetry_mocks):
        mock_get, mock_subprocess = telemetry_mocks

        utils.scarf_analytics()

        mock_get.assert_called_once()
        mock_subprocess.assert_called_once_with(["nvidia-smi"], stderr=subprocess.DEVNULL)
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://packages.unstructured.io/python-telemetry"
        params = call_args[1]["params"]
        assert set(params.keys()) == {"version", "platform", "python", "arch", "gpu", "dev"}
        assert call_args[1]["timeout"] == 10

    @pytest.mark.parametrize(
        ("env_name", "value"),
        [
            ("DO_NOT_TRACK", "true"),
            ("DO_NOT_TRACK", "false"),
            ("SCARF_NO_ANALYTICS", "yes"),
            ("SCARF_NO_ANALYTICS", "0"),
        ],
        ids=["do-not-track-true", "do-not-track-false", "scarf-yes", "scarf-zero"],
    )
    def it_does_not_probe_or_send_when_either_opt_out_is_non_empty(
        self, monkeypatch, telemetry_mocks, env_name, value
    ):
        mock_get, mock_subprocess = telemetry_mocks
        _apply_telemetry_env(monkeypatch, {env_name: value})

        assert utils._telemetry_opt_out() is True
        utils.scarf_analytics()

        mock_get.assert_not_called()
        mock_subprocess.assert_not_called()

    @pytest.mark.parametrize(
        ("env_name", "value"),
        [
            ("DO_NOT_TRACK", ""),
            ("DO_NOT_TRACK", " \t "),
            ("SCARF_NO_ANALYTICS", ""),
            ("SCARF_NO_ANALYTICS", " \t "),
        ],
        ids=["do-not-track-empty", "do-not-track-whitespace", "scarf-empty", "scarf-whitespace"],
    )
    def it_sends_when_opt_out_is_empty_or_whitespace_only(
        self, monkeypatch, telemetry_mocks, env_name, value
    ):
        mock_get, mock_subprocess = telemetry_mocks
        _apply_telemetry_env(monkeypatch, {env_name: value})

        assert utils._telemetry_opt_out() is False
        utils.scarf_analytics()

        mock_get.assert_called_once()
        mock_subprocess.assert_called_once_with(["nvidia-smi"], stderr=subprocess.DEVNULL)

    @pytest.mark.parametrize(
        ("version_val", "expected_dev"),
        [("1.2.3.dev0", "true"), ("1.2.3", "false")],
        ids=["dev-version", "release-version"],
    )
    def it_sends_telemetry_with_correct_dev_param(
        self, monkeypatch, telemetry_mocks, version_val, expected_dev
    ):
        mock_get, mock_subprocess = telemetry_mocks
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

    def it_suppresses_requests_exceptions(self, telemetry_mocks):
        mock_get, mock_subprocess = telemetry_mocks
        mock_get.side_effect = requests.RequestException("network error")

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
    def it_sends_with_gpu_false_when_the_probe_fails(self, telemetry_mocks, exc):
        mock_get, mock_subprocess = telemetry_mocks
        mock_subprocess.side_effect = exc

        utils.scarf_analytics()  # does not raise

        mock_get.assert_called_once()
        assert mock_get.call_args[1]["params"]["gpu"] == "False"
        mock_subprocess.assert_called_once_with(["nvidia-smi"], stderr=subprocess.DEVNULL)

    def it_import_unstructured_succeeds_when_opted_out(self):
        """Importing while opted out remains non-fatal."""
        project_root = Path(__file__).resolve().parent.parent
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in ("DO_NOT_TRACK", "SCARF_NO_ANALYTICS")
        }
        env.update(
            {
                "DO_NOT_TRACK": "false",
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

    def it_import_unstructured_runs_telemetry_once_by_default(self):
        """The package initializer sends exactly one ping when no opt-out is set."""
        project_root = Path(__file__).resolve().parent.parent
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in ("DO_NOT_TRACK", "SCARF_NO_ANALYTICS")
        }
        env["PYTHONPATH"] = str(project_root)
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
            "Import without an opt-out should run telemetry exactly once (requests.get and "
            "subprocess.check_output each called once). "
            f"stderr={result.stderr!r} stdout={result.stdout!r}"
        )
