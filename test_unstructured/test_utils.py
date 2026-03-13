from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from unstructured import utils
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, NarrativeText, Title


@pytest.fixture()
def input_data():
    return [
        {"text": "This is a sentence."},
        {"text": "This is another sentence.", "meta": {"score": 0.1}},
    ]


@pytest.fixture()
def output_jsonl_file(tmp_path):
    return os.path.join(tmp_path, "output.jsonl")


@pytest.fixture()
def input_jsonl_file(tmp_path, input_data):
    file_path = os.path.join(tmp_path, "input.jsonl")
    with open(file_path, "w+") as input_file:
        input_file.writelines([json.dumps(obj) + "\n" for obj in input_data])
    return file_path


def test_save_as_jsonl(input_data, output_jsonl_file):
    utils.save_as_jsonl(input_data, output_jsonl_file)
    with open(output_jsonl_file) as output_file:
        file_data = [json.loads(line) for line in output_file]
    assert file_data == input_data


def test_read_as_jsonl(input_jsonl_file, input_data):
    file_data = utils.read_from_jsonl(input_jsonl_file)
    assert file_data == input_data


def test_requires_dependencies_decorator():
    @utils.requires_dependencies(dependencies="numpy")
    def test_func():
        import numpy  # noqa: F401

    test_func()


def test_requires_dependencies_decorator_multiple():
    @utils.requires_dependencies(dependencies=["numpy", "pandas"])
    def test_func():
        import numpy  # noqa: F401
        import pandas  # noqa: F401

    test_func()


def test_requires_dependencies_decorator_import_error():
    @utils.requires_dependencies(dependencies="not_a_package")
    def test_func():
        import not_a_package  # noqa: F401

    with pytest.raises(ImportError):
        test_func()


def test_requires_dependencies_decorator_import_error_multiple():
    @utils.requires_dependencies(dependencies=["not_a_package", "numpy"])
    def test_func():
        import not_a_package  # noqa: F401
        import numpy  # noqa: F401

    with pytest.raises(ImportError):
        test_func()


def test_requires_dependencies_decorator_in_class():
    @utils.requires_dependencies(dependencies="numpy")
    class TestClass:
        def __init__(self):
            import numpy  # noqa: F401

    TestClass()


@pytest.mark.parametrize("iterator", [[0, 1], (0, 1), range(10), [0], (0,), range(1)])
def test_first_gives_first(iterator):
    assert utils.first(iterator) == 0


@pytest.mark.parametrize("iterator", [[], ()])
def test_first_raises_if_empty(iterator):
    with pytest.raises(ValueError):
        utils.first(iterator)


@pytest.mark.parametrize("iterator", [[0], (0,), range(1)])
def test_only_gives_only(iterator):
    assert utils.first(iterator) == 0


@pytest.mark.parametrize("iterator", [[0, 1], (0, 1), range(10)])
def test_only_raises_when_len_more_than_1(iterator):
    with pytest.raises(ValueError):
        utils.only(iterator)


@pytest.mark.parametrize("iterator", [[], ()])
def test_only_raises_if_empty(iterator):
    with pytest.raises(ValueError):
        utils.only(iterator)


@pytest.mark.parametrize(
    ("coords1", "coords2", "text1", "text2", "nested_error_tolerance_px", "expectation"),
    [
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "Some lovely title",
            "Some lovely text",
            5,  # large nested_error_tolerance_px
            {
                "overlapping_elements": ["Title(ix=0)", "NarrativeText(ix=1)"],
                "parent_element": "Title(ix=0)",
                "overlapping_case": "nested NarrativeText in Title",
                "overlap_percentage": "100%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "Some lovely title",
            "Some lovely text",
            1,  # small nested_error_tolerance_px
            {
                "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                "parent_element": None,
                "overlapping_case": "partial overlap sharing 50.0% of the text from1. "
                "NarrativeText(2-gram)",
                "overlap_percentage": "11.11%",
                "metadata": {
                    "largest_ngram_percentage": 50.0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "Some lovely title",
            "Some lovely title",  # same title
            1,
            {
                "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                "parent_element": None,
                "overlapping_case": "partial overlap with duplicate text",
                "overlap_percentage": "11.11%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "Some lovely title",
            "",  # empty title
            1,
            {
                "overlapping_elements": ["1. NarrativeText(ix=1)", "0. Title(ix=0)"],
                "parent_element": None,
                "overlapping_case": ("partial overlap with empty content in 1. NarrativeText"),
                "overlap_percentage": "11.11%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "",  # empty 1st title
            "Some lovely title",
            1,
            {
                "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                "parent_element": None,
                "overlapping_case": "partial overlap with empty content in 0. Title",
                "overlap_percentage": "11.11%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((4, 5), (4, 8), (7, 8), (7, 5)),
            ((2, 3), (2, 6), (5, 6), (5, 3)),
            "Some lovely title",
            "Something totally different here",  # diff text
            1,
            {
                "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                "parent_element": None,
                "overlapping_case": "partial overlap without sharing text",
                "overlap_percentage": "11.11%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "5.88%",
                    "max_area": "9pxˆ2",
                    "min_area": "9pxˆ2",
                    "total_area": "18pxˆ2",
                },
            },
        ),
        (
            ((5, 6), (5, 10), (8, 10), (8, 6)),  # diff coordinates
            ((1, 3), (2, 7), (6, 7), (5, 3)),
            "Some lovely title",
            "Some lovely text",
            1,
            {
                "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                "parent_element": None,
                "overlapping_case": "Small partial overlap",
                "overlap_percentage": "8.33%",
                "metadata": {
                    "largest_ngram_percentage": 0,
                    "overlap_percentage_total": "3.23%",
                    "max_area": "20pxˆ2",
                    "min_area": "12pxˆ2",
                    "total_area": "32pxˆ2",
                },
            },
        ),
    ],
)
def test_catch_overlapping_and_nested_bboxes(
    coords1, coords2, text1, text2, nested_error_tolerance_px, expectation
):
    elements = [
        Title(
            text=text1,
            coordinates=coords1,
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
        NarrativeText(
            text=text2,
            coordinates=coords2,
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
    ]
    overlapping_flag, overlapping_cases = utils.catch_overlapping_and_nested_bboxes(
        elements,
        nested_error_tolerance_px,
        sm_overlap_threshold=10.0,
    )
    assert overlapping_flag is True
    assert overlapping_cases[0] == expectation


def test_catch_overlapping_and_nested_bboxes_non_overlapping_case():
    elements = [
        Title(
            text="Some lovely title",
            coordinates=((4, 6), (4, 7), (7, 7), (7, 6)),
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
        NarrativeText(
            text="Some lovely text",
            coordinates=((6, 8), (6, 9), (9, 9), (9, 8)),
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
    ]
    overlapping_flag, overlapping_cases = utils.catch_overlapping_and_nested_bboxes(
        elements,
        1,
        sm_overlap_threshold=10.0,
    )
    assert overlapping_flag is False
    assert overlapping_cases == []


def test_only_returns_singleton_iterable():
    singleton_iterable = [42]
    result = utils.only(singleton_iterable)
    assert result == 42


def test_only_raises_on_non_singleton_iterable():
    singleton_iterable = [42, 0]
    with pytest.raises(ValueError):
        utils.only(singleton_iterable)


def test_calculate_shared_ngram_percentage_returns_null_vals_for_empty_str():
    str1 = ""
    str2 = "banana orange pineapple"
    n = 2
    percent, common_ngrams = utils.calculate_shared_ngram_percentage(str1, str2, n)
    assert percent == 0
    assert not bool(common_ngrams)


class DescribeGroupElementsByParentId:
    """Unit tests for group_elements_by_parent_id function."""

    def it_groups_elements_by_parent_id_with_orphans_in_none_group(self):
        e1 = Title("Title 1")
        e1.metadata.parent_id = "parent_A"
        e2 = NarrativeText("Child of A")
        e2.metadata.parent_id = "parent_A"
        e3 = NarrativeText("Orphan 1")  # parent_id = None
        e4 = Title("Title 2")
        e4.metadata.parent_id = "parent_B"
        e5 = NarrativeText("Orphan 2")  # parent_id = None

        elements = [e1, e2, e3, e4, e5]
        result = utils.group_elements_by_parent_id(elements)

        assert list(result.keys()) == ["parent_A", None, "parent_B"]
        assert [e.text for e in result["parent_A"]] == ["Title 1", "Child of A"]
        assert [e.text for e in result[None]] == ["Orphan 1", "Orphan 2"]
        assert [e.text for e in result["parent_B"]] == ["Title 2"]

    def it_assigns_orphans_to_previous_element_group_when_assign_orphans_is_true(self):
        e1 = Title("Title 1")
        e1.metadata.parent_id = "parent_A"
        e2 = NarrativeText("Child of A")
        e2.metadata.parent_id = "parent_A"
        e3 = NarrativeText("Orphan 1")  # parent_id = None
        e4 = Title("Title 2")
        e4.metadata.parent_id = "parent_B"
        e5 = NarrativeText("Orphan 2")  # parent_id = None

        elements = [e1, e2, e3, e4, e5]
        result = utils.group_elements_by_parent_id(elements, assign_orphans=True)

        assert list(result.keys()) == ["parent_A", "parent_B"]
        assert [e.text for e in result["parent_A"]] == ["Title 1", "Child of A", "Orphan 1"]
        assert [e.text for e in result["parent_B"]] == ["Title 2", "Orphan 2"]

    def it_keeps_first_orphan_in_none_group_when_assign_orphans_is_true(self):
        e1 = NarrativeText("First orphan")  # parent_id = None
        e2 = Title("Title 1")
        e2.metadata.parent_id = "parent_A"
        e3 = NarrativeText("Orphan 2")  # parent_id = None

        elements = [e1, e2, e3]
        result = utils.group_elements_by_parent_id(elements, assign_orphans=True)

        assert list(result.keys()) == [None, "parent_A"]
        assert [e.text for e in result[None]] == ["First orphan"]
        assert [e.text for e in result["parent_A"]] == ["Title 1", "Orphan 2"]


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
            {"SCARF_NO_ANALYTICS": "true"},
            {"SCARF_NO_ANALYTICS": "yes"},
            {"SCARF_NO_ANALYTICS": "on"},
            {"SCARF_NO_ANALYTICS": "1"},
            {"SCARF_NO_ANALYTICS": "TRUE"},
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
            "SCARF_NO_ANALYTICS=true",
            "SCARF_NO_ANALYTICS=yes",
            "SCARF_NO_ANALYTICS=on",
            "SCARF_NO_ANALYTICS=1",
            "SCARF_NO_ANALYTICS=TRUE",
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
        [OSError(), PermissionError("nvidia-smi denied")],
        ids=["OSError", "PermissionError"],
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
        env = {
            **os.environ,
            "DO_NOT_TRACK": "1",
            "UNSTRUCTURED_TELEMETRY_ENABLED": "",
            "PYTHONPATH": str(project_root),
        }
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

    def it_import_unstructured_succeeds_with_opt_in(self):
        """Import path with opt-in env does not crash (integration-style)."""
        project_root = Path(__file__).resolve().parent.parent
        env = {
            **os.environ,
            "UNSTRUCTURED_TELEMETRY_ENABLED": "true",
            "DO_NOT_TRACK": "",
            "PYTHONPATH": str(project_root),
        }
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
