"""Partitioning when onnxruntime is installed but fails to load (issue #3981).

Each case runs in a fresh interpreter. In fault mode the child prepends a meta-path finder that
returns the real onnxruntime spec (so `find_spec` succeeds) with its loader wrapped to raise the
Windows DLL-initialization `ImportError` on execution. Outputs are compared with a healthy twin
run in the same environment rather than with a hardcoded, environment-specific text hash.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject

from test_unstructured.unit_utils import example_doc_path

_FAULT_MESSAGE = (
    "DLL load failed while importing onnxruntime_pybind11_state: "
    "A dynamic link library (DLL) initialization routine failed."
)
_FORM_VALUES = ("Jane Doe", "1990-01-01", "123 Main Street")
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_UNSTRUCTURED_ORIGIN = os.path.realpath(importlib.util.find_spec("unstructured").origin)

_CHILD_SCRIPT = r"""
import hashlib
import importlib.abc
import importlib.util
import json
import logging
import sys

spec_in = json.loads(sys.argv[1])
state = {"fault_exec_count": 0, "raised": None}
log_messages = []


class _Collector(logging.Handler):
    def emit(self, record):
        log_messages.append(record.getMessage())


class _FaultyLoader(importlib.abc.Loader):
    def __init__(self, real_loader):
        self._real_loader = real_loader

    def create_module(self, spec):
        return self._real_loader.create_module(spec)

    def exec_module(self, module):
        state["fault_exec_count"] += 1
        state["raised"] = ImportError(spec_in["fault_message"])
        raise state["raised"]


class _FaultyFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname != "onnxruntime":
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            real_spec = finder.find_spec(fullname, path, target)
            if real_spec is not None:
                real_spec.loader = _FaultyLoader(real_spec.loader)
                return real_spec
        return None


logging.getLogger().setLevel(logging.INFO)
for logger in (logging.getLogger(), logging.getLogger("unstructured")):
    logger.addHandler(_Collector())
if spec_in["fault"]:
    sys.meta_path.insert(0, _FaultyFinder())

ort_spec = importlib.util.find_spec("onnxruntime")
result = {
    "ort_find_spec_ok": ort_spec is not None and ort_spec.origin is not None,
    "ort_loader_wrapped": isinstance(getattr(ort_spec, "loader", None), _FaultyLoader),
    "stage": "import",
    "outputs": None,
}
try:
    if spec_in["entry"] == "image":
        from unstructured.partition.image import partition_image as partition
    else:
        from unstructured.partition.pdf import partition_pdf as partition
    import unstructured

    result["unstructured_origin"] = unstructured.__file__
    result["stage"] = "call"
    outputs, input_sha256, text_sha256 = {}, {}, {}
    for path in spec_in["paths"]:
        with open(path, "rb") as f:
            input_sha256[path] = hashlib.sha256(f.read()).hexdigest()
        elements = list(partition(filename=path, **spec_in["kwargs"]))
        outputs[path] = [element.to_dict() for element in elements]
        text = "\n\n".join(element.text for element in elements)
        text_sha256[path] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    result.update(
        stage="returned", outputs=outputs, input_sha256=input_sha256, text_sha256=text_sha256
    )
except Exception as exc:
    result["exc_type"] = f"{type(exc).__module__}.{type(exc).__qualname__}"
    result["exc_message"] = str(exc)
    result["exc_is_injected"] = state["raised"] is not None and exc is state["raised"]
    result["exc_chain"] = [repr(exc.__cause__), repr(exc.__context__)]

result["fault_exec_count"] = state["fault_exec_count"]
result["onnxruntime_module_count"] = sum(
    1 for name in list(sys.modules) if name == "onnxruntime" or name.startswith("onnxruntime.")
)
if spec_in["check_dependency_exists"]:
    from unstructured.utils import dependency_exists

    result["inference_dependency_exists"] = dependency_exists("unstructured_inference")
result["log_messages"] = log_messages
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(result, f, default=str, sort_keys=True)
"""


def _run_child(
    tmp_path: pathlib.Path,
    label: str,
    *,
    fault: bool,
    paths: list[str],
    partition_kwargs: dict[str, Any],
    entry: str = "pdf",
    check_dependency_exists: bool = False,
) -> dict[str, Any]:
    """Run one case in a fresh `sys.executable` child and return its JSON report."""
    spec = {
        "fault": fault,
        "fault_message": _FAULT_MESSAGE,
        "entry": entry,
        "paths": paths,
        "kwargs": partition_kwargs,
        "check_dependency_exists": check_dependency_exists,
    }
    report_path = tmp_path / f"{label}.json"
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT, json.dumps(spec), str(report_path)],
        cwd=_REPO_ROOT,
        env={**os.environ, "DO_NOT_TRACK": "1"},
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["stderr"] = proc.stderr
    return report


def _context(report: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in report.items() if k not in ("outputs", "log_messages")}


def _assert_onnxruntime_never_loaded(fault: dict[str, Any]) -> None:
    assert fault["ort_find_spec_ok"] is True
    assert fault["ort_loader_wrapped"] is True
    assert fault["stage"] == "returned", _context(fault)
    assert fault["fault_exec_count"] == 0
    assert fault["onnxruntime_module_count"] == 0
    assert os.path.realpath(fault["unstructured_origin"]) == _UNSTRUCTURED_ORIGIN


def _assert_fault_matches_healthy(
    tmp_path: pathlib.Path,
    label: str,
    paths: list[str],
    fault_kwargs: dict[str, Any],
    healthy_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    healthy_kwargs = fault_kwargs if healthy_kwargs is None else healthy_kwargs
    healthy = _run_child(
        tmp_path, f"{label}-healthy", fault=False, paths=paths, partition_kwargs=healthy_kwargs
    )
    fault = _run_child(
        tmp_path, f"{label}-fault", fault=True, paths=paths, partition_kwargs=fault_kwargs
    )

    assert healthy["stage"] == "returned", _context(healthy)
    assert healthy["ort_loader_wrapped"] is False
    assert all(healthy["outputs"][path] for path in paths), "healthy twin returned no elements"
    _assert_onnxruntime_never_loaded(fault)
    assert fault["input_sha256"] == healthy["input_sha256"]
    assert fault["outputs"] == healthy["outputs"]
    assert fault["text_sha256"] == healthy["text_sha256"]
    return healthy


def _write_filled_form_pdf(path: pathlib.Path) -> str:
    """Write a blank page whose only text is filled text-field (/Tx) widget values."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    for index, value in enumerate(_FORM_VALUES):
        y = 700 - 60 * index
        rect = [FloatObject(72), FloatObject(y), FloatObject(360), FloatObject(y + 24)]
        widget = {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Tx"),
            NameObject("/T"): TextStringObject(f"field{index}"),
            NameObject("/V"): TextStringObject(value),
            NameObject("/Rect"): ArrayObject(rect),
        }
        writer.add_annotation(page_number=0, annotation=DictionaryObject(widget))
    with path.open("wb") as f:
        writer.write(f)
    return str(path)


def test_partition_pdf_imports_when_onnxruntime_is_installed_but_fails_to_load(tmp_path):
    healthy = _run_child(tmp_path, "import-healthy", fault=False, paths=[], partition_kwargs={})
    fault = _run_child(tmp_path, "import-fault", fault=True, paths=[], partition_kwargs={})

    assert healthy["stage"] == "returned", _context(healthy)
    _assert_onnxruntime_never_loaded(fault)


def test_fast_strategy_works_when_onnxruntime_fails_to_load(tmp_path):
    paths = [example_doc_path("pdf/embedded-images.pdf")]
    _assert_fault_matches_healthy(tmp_path, "fast", paths, {"strategy": "fast"})


def test_fast_strategy_keeps_link_annotations_when_onnxruntime_fails_to_load(tmp_path):
    paths = [
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        example_doc_path("pdf/embedded-link.pdf"),
    ]
    healthy = _assert_fault_matches_healthy(tmp_path, "links", paths, {"strategy": "fast"})

    links = [
        link
        for path in paths
        for element in healthy["outputs"][path]
        for link in element["metadata"].get("links") or []
    ]
    assert links, "healthy twin has no link metadata, so this case would be vacuous"


def test_fast_strategy_keeps_form_field_values_when_onnxruntime_fails_to_load(tmp_path):
    form_pdf = _write_filled_form_pdf(tmp_path / "filled-form.pdf")
    healthy = _assert_fault_matches_healthy(tmp_path, "form", [form_pdf], {"strategy": "fast"})

    healthy_text = "\n".join(element["text"] for element in healthy["outputs"][form_pdf])
    assert all(value in healthy_text for value in _FORM_VALUES), healthy_text


def test_auto_strategy_matches_healthy_fast_when_onnxruntime_fails_to_load(tmp_path):
    paths = [
        example_doc_path("pdf/embedded-images.pdf"),
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        example_doc_path("pdf/embedded-link.pdf"),
    ]
    _assert_fault_matches_healthy(
        tmp_path, "auto", paths, {"strategy": "auto"}, healthy_kwargs={"strategy": "fast"}
    )


@pytest.mark.parametrize(
    ("entry", "doc", "partition_kwargs"),
    [
        ("pdf", "pdf/embedded-images.pdf", {"strategy": "hi_res"}),
        ("pdf", "pdf/embedded-images.pdf", {"strategy": "auto", "infer_table_structure": True}),
        ("pdf", "pdf/embedded-images.pdf", {"strategy": "ocr_only"}),
        ("image", "img/layout-parser-paper-fast.jpg", {}),
    ],
    ids=["hi_res", "auto_tables", "ocr_only", "image_default"],
)
def test_inference_strategies_still_raise_the_raw_load_error(
    tmp_path, entry, doc, partition_kwargs
):
    fault = _run_child(
        tmp_path,
        "control",
        fault=True,
        paths=[example_doc_path(doc)],
        partition_kwargs=partition_kwargs,
        entry=entry,
        check_dependency_exists=True,
    )

    assert fault["ort_find_spec_ok"] is True
    assert fault["ort_loader_wrapped"] is True
    assert fault["outputs"] is None, _context(fault)
    assert fault["exc_type"] == "builtins.ImportError"
    assert fault["exc_message"] == _FAULT_MESSAGE
    assert fault["exc_is_injected"] is True
    assert fault["fault_exec_count"] >= 1
    assert fault["inference_dependency_exists"] is True
    for marker in ("Following dependencies are missing", "PDF text extraction failed"):
        assert not any(marker in message for message in fault["log_messages"])
        assert marker not in fault["stderr"]
