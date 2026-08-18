"""Hermetic tests for per-invocation partition runtime telemetry."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from unittest.mock import Mock

import pytest

from unstructured import telemetry
from unstructured.documents.elements import (
    CompositeElement,
    ElementMetadata,
    Footer,
    Header,
    Image,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)


@pytest.fixture(autouse=True)
def runtime_session(monkeypatch):
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("SCARF_NO_ANALYTICS", raising=False)
    session = Mock()
    session.get.return_value = Mock()
    monkeypatch.setattr(telemetry.requests, "Session", Mock(return_value=session))
    return session


@pytest.fixture
def captured_events(monkeypatch):
    events: list[dict[str, object]] = []
    monkeypatch.setattr(telemetry, "_schedule_delivery", lambda build: events.append(build()))
    return events


def _named_partitioner(name, implementation, document_type="txt"):
    implementation.__name__ = name
    return telemetry.partition_runtime_telemetry(document_type)(implementation)


def test_real_public_partitioner_is_instrumented_after_final_processing(captured_events):
    from unstructured.partition.text import partition_text

    result = partition_text(text="A telemetry test sentence.", chunking_strategy="basic")

    assert result
    assert captured_events[0]["partitioner"] == "partition_text"
    assert captured_events[0]["document_type"] == "txt"
    assert captured_events[0]["chunking_strategy"] == "basic"
    assert captured_events[0]["num_elements"] == len(result)


def test_success_preserves_result_and_reports_exact_final_counts(captured_events):
    table = Table("table", metadata=ElementMetadata(text_as_html="<table></table>"))
    elements = [
        Title("title"),
        NarrativeText("narrative"),
        ListItem("item"),
        table,
        TableChunk("chunk"),
        Image("image"),
        Header("header"),
        Footer("footer"),
        CompositeElement("composite"),
        Text("other"),
    ]
    elements[0].embeddings = [0.5]
    result = elements
    partition_text = _named_partitioner("partition_text", lambda *, chunking_strategy=None: result)

    actual = partition_text(chunking_strategy="by_title")

    assert actual is result
    assert len(captured_events) == 1
    event = captured_events[0]
    assert event["outcome"] == "success"
    assert event["document_type"] == "txt"
    assert event["strategy_requested"] == "not_applicable"
    assert event["strategy_used"] == "not_applicable"
    assert event["table_extraction"] == "false"
    assert event["ocr_used"] == "false"
    assert event["chunking_strategy"] == "by_title"
    assert event["has_embeddings"] == "true"
    assert event["num_documents"] == 1
    assert event["num_elements"] == 10
    assert event["num_titles"] == 1
    assert event["num_narrative_text"] == 1
    assert event["num_list_items"] == 1
    assert event["num_tables"] == 2
    assert event["num_images"] == 1
    assert event["num_headers"] == 1
    assert event["num_footers"] == 1
    assert event["num_composite_elements"] == 1
    assert event["num_other_elements"] == 1
    assert event["num_elements"] == sum(
        event[key]
        for key in (
            "num_titles",
            "num_narrative_text",
            "num_list_items",
            "num_tables",
            "num_images",
            "num_headers",
            "num_footers",
            "num_composite_elements",
            "num_other_elements",
        )
    )


def test_original_processing_exception_is_re_raised_unchanged(captured_events):
    expected = RuntimeError("private document detail")

    def fail():
        raise expected

    partition_pdf = _named_partitioner("partition_pdf", fail, "pdf")

    with pytest.raises(RuntimeError) as exc_info:
        partition_pdf()

    assert exc_info.value is expected
    assert captured_events == [
        {
            "schema_version": 1,
            "version": telemetry.__version__,
            "platform": captured_events[0]["platform"],
            "python": captured_events[0]["python"],
            "arch": captured_events[0]["arch"],
            "partitioner": "partition_pdf",
            "outcome": "error",
            "document_type": "pdf",
        }
    ]
    assert "private document detail" not in repr(captured_events[0])
    assert "fail" in [frame.name for frame in traceback.extract_tb(exc_info.value.__traceback__)]


def test_telemetry_preparation_failure_does_not_change_result(monkeypatch):
    expected = [Text("ok")]
    partition_text = _named_partitioner("partition_text", lambda: expected)
    monkeypatch.setattr(telemetry, "_base_params", Mock(side_effect=RuntimeError("broken")))

    assert partition_text() is expected

    monkeypatch.setattr(telemetry, "_prepare_invocation", Mock(side_effect=RuntimeError("broken")))
    assert partition_text() is expected


def test_caller_process_control_exception_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(telemetry, "_telemetry_opt_out", Mock(side_effect=KeyboardInterrupt()))
    partition_text = _named_partitioner("partition_text", lambda: [Text("not reached")])

    with pytest.raises(KeyboardInterrupt):
        partition_text()


def test_delivery_failure_is_contained_and_releases_slot(runtime_session):
    runtime_session.get.side_effect = KeyboardInterrupt()
    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)

    telemetry._deliver({"schema_version": 1})

    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)
    telemetry._DELIVERY_SLOT.release()


def test_delivery_disables_environment_redirects_retries_and_body_download(
    runtime_session,
):
    session = runtime_session
    response = session.get.return_value
    params = {"schema_version": 1}
    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)

    telemetry._deliver(params)

    assert session.trust_env is False
    assert session.mount.call_count == 2
    for mount_call in session.mount.call_args_list:
        assert mount_call.args[1].max_retries.total == 0
    session.get.assert_called_once_with(
        "https://packages.unstructured.io/v1/partition",
        params=params,
        timeout=(0.2, 0.2),
        allow_redirects=False,
        stream=True,
    )
    response.close.assert_called_once()
    session.close.assert_called_once()
    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)
    telemetry._DELIVERY_SLOT.release()


def test_thread_start_failure_is_contained_and_releases_slot(monkeypatch):
    thread = Mock()
    thread.start.side_effect = RuntimeError("no thread capacity")
    monkeypatch.setattr(telemetry.threading, "Thread", Mock(return_value=thread))
    partition_text = _named_partitioner("partition_text", lambda: [Text("ok")])

    assert partition_text()[0].text == "ok"
    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)
    telemetry._DELIVERY_SLOT.release()


@pytest.mark.parametrize("variable", ["DO_NOT_TRACK", "SCARF_NO_ANALYTICS"])
def test_opt_out_skips_all_runtime_telemetry_work(monkeypatch, variable):
    monkeypatch.setenv(variable, " false ")
    start = Mock(side_effect=AssertionError("must not inspect arguments"))
    schedule = Mock(side_effect=AssertionError("must not schedule delivery"))
    monkeypatch.setattr(telemetry, "_new_invocation", start)
    monkeypatch.setattr(telemetry, "_schedule_delivery", schedule)
    expected = [Text("ok")]
    partition_text = _named_partitioner("partition_text", lambda: expected)

    assert partition_text() is expected
    start.assert_not_called()
    schedule.assert_not_called()


def test_opt_out_does_not_inspect_poison_argument(monkeypatch):
    class Poison:
        def __str__(self):
            raise AssertionError("telemetry inspected caller data")

    monkeypatch.setenv("DO_NOT_TRACK", "1")
    expected = [Text("ok")]
    partition_image = _named_partitioner("partition_image", lambda strategy=None: expected, "png")

    assert partition_image(strategy=Poison()) is expected


def test_nested_public_dispatch_emits_only_outer_event(captured_events):
    inner = _named_partitioner("partition_html", lambda: [Title("nested")], "html")
    outer = _named_partitioner("partition_email", inner, "eml")

    outer()

    assert len(captured_events) == 1
    assert captured_events[0]["partitioner"] == "partition_email"
    assert captured_events[0]["document_type"] == "eml"


def test_nested_auto_dispatch_cannot_replace_outer_document_type(captured_events):
    def nested():
        telemetry.set_partition_document_type("pdf")
        return [Title("nested")]

    inner = _named_partitioner("partition", nested)
    outer = _named_partitioner("partition_email", inner, "eml")

    outer()

    assert captured_events[0]["document_type"] == "eml"


def test_preparation_failure_still_suppresses_nested_event(monkeypatch, captured_events):
    monkeypatch.setattr(telemetry, "_prepare_invocation", Mock(side_effect=RuntimeError("broken")))
    inner = _named_partitioner("partition_html", lambda: [Title("nested")], "html")
    outer = _named_partitioner("partition_email", inner, "eml")

    outer()

    assert len(captured_events) == 1
    assert captured_events[0]["partitioner"] == "partition_email"


def test_invocation_context_is_reset_after_processing_error(captured_events):
    def fail():
        raise RuntimeError("processing failed")

    failing = _named_partitioner("partition_pdf", fail, "pdf")
    succeeding = _named_partitioner("partition_text", lambda: [Text("ok")])

    with pytest.raises(RuntimeError):
        failing()
    assert succeeding()[0].text == "ok"

    assert [event["outcome"] for event in captured_events] == ["error", "success"]


def test_api_batch_reports_truthful_document_and_element_counts(captured_events):
    documents = [[Title("one")], [], [Text("three"), ListItem("four")]]
    partition_multiple = _named_partitioner(
        "partition_multiple_via_api", lambda **request_kwargs: documents, None
    )

    assert partition_multiple(strategy="fast", chunking_strategy="basic") is documents

    event = captured_events[0]
    assert event["num_documents"] == 3
    assert event["num_elements"] == 3
    assert event["strategy_requested"] == "fast"
    assert event["strategy_used"] == "unknown"
    assert event["chunking_strategy"] == "basic"


def test_field_normalization_uses_only_fixed_enums(monkeypatch, captured_events):
    monkeypatch.setattr(telemetry.platform, "system", lambda: "Plan 9")
    monkeypatch.setattr(telemetry.platform, "machine", lambda: "mystery-chip")
    partition_other = _named_partitioner("caller_supplied_name", lambda: [], "secret/type")

    partition_other()

    event = captured_events[0]
    assert event["platform"] == "Other"
    assert event["arch"] == "other"
    assert event["partitioner"] == "other"
    assert event["document_type"] == "other"


def test_actual_execution_markers_are_reported(captured_events):
    def process(strategy="hi_res"):
        telemetry.set_partition_strategy_used("ocr_only")
        telemetry.mark_partition_ocr_used()
        telemetry.mark_partition_table_extraction()
        return []

    partition_image = _named_partitioner("partition_image", process, "png")

    partition_image(strategy="auto")

    event = captured_events[0]
    assert event["strategy_requested"] == "auto"
    assert event["strategy_used"] == "ocr_only"
    assert event["ocr_used"] == "true"
    assert event["table_extraction"] == "true"


def test_omitted_image_strategy_uses_public_signature_default(captured_events):
    def process(strategy="hi_res"):
        telemetry.set_partition_strategy_used(strategy)
        return []

    partition_image = _named_partitioner("partition_image", process, "png")

    partition_image()

    assert captured_events[0]["strategy_requested"] == "hi_res"
    assert captured_events[0]["strategy_used"] == "hi_res"


def test_direct_image_records_type_resolved_by_processing(captured_events):
    def process():
        telemetry.set_partition_document_type("JPEG")
        return []

    partition_image = _named_partitioner("partition_image", process, None)

    partition_image()

    assert captured_events[0]["document_type"] == "jpg"


def test_structured_remote_or_serialized_table_does_not_claim_local_extraction(captured_events):
    result = [Table("table", metadata=ElementMetadata(text_as_html="<table></table>"))]
    partition_api = _named_partitioner("partition_via_api", lambda: result, None)

    partition_api()

    assert captured_events[0]["table_extraction"] == "false"


def test_structured_native_table_reports_local_extraction(captured_events):
    result = [Table("table", metadata=ElementMetadata(text_as_html="<table></table>"))]
    partition_csv = _named_partitioner("partition_csv", lambda: result, "csv")

    partition_csv()

    assert captured_events[0]["table_extraction"] == "true"


def test_full_result_is_not_scanned_when_delivery_slot_is_occupied():
    class PoisonDocument:
        def __iter__(self):
            raise AssertionError("dropped event inspected partition result")

    assert telemetry._DELIVERY_SLOT.acquire(blocking=False)
    try:
        telemetry._finish_success(
            telemetry._new_invocation("partition_text"),
            PoisonDocument(),
        )
    finally:
        telemetry._DELIVERY_SLOT.release()


def test_pid_change_resets_inherited_delivery_and_invocation_state(monkeypatch):
    original_pid = telemetry._PROCESS_ID
    original_slot = telemetry._DELIVERY_SLOT
    original_context = telemetry._CURRENT_INVOCATION
    token = original_context.set(telemetry._new_invocation("partition_email"))
    try:
        assert original_slot.acquire(blocking=False)
        monkeypatch.setattr(telemetry.os, "getpid", lambda: original_pid + 1)

        telemetry._ensure_process_state()

        assert telemetry._CURRENT_INVOCATION.get() is None
        assert telemetry._DELIVERY_SLOT.acquire(blocking=False)
        telemetry._DELIVERY_SLOT.release()
    finally:
        original_slot.release()
        original_context.reset(token)
        telemetry._DELIVERY_SLOT = original_slot
        telemetry._CURRENT_INVOCATION = original_context
        telemetry._PROCESS_ID = original_pid


def test_stuck_transport_never_waits_and_capacity_is_bounded(runtime_session):
    entered = threading.Event()
    release = threading.Event()
    session = runtime_session
    session.get.side_effect = lambda *a, **k: (entered.set(), release.wait(2))
    partition_text = _named_partitioner("partition_text", lambda: [Text("ok")])

    started = time.monotonic()
    first_result = partition_text()
    elapsed = time.monotonic() - started
    assert entered.wait(0.5)
    assert elapsed < 0.5
    assert first_result[0].text == "ok"

    # The sole slot is occupied: another event is dropped without another worker or request.
    assert partition_text()[0].text == "ok"
    assert session.get.call_count == 1
    assert session.get.call_args.args[0] == "https://packages.unstructured.io/v1/partition"
    assert session.get.call_args.kwargs == {
        "params": session.get.call_args.kwargs["params"],
        "timeout": (0.2, 0.2),
        "allow_redirects": False,
        "stream": True,
    }
    assert session.trust_env is False
    assert session.mount.call_count == 2
    release.set()
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        if telemetry._DELIVERY_SLOT.acquire(blocking=False):
            telemetry._DELIVERY_SLOT.release()
            break
        time.sleep(0.01)
    else:
        pytest.fail("delivery worker did not release its bounded slot")
    session.close.assert_called_once()


def test_blocked_daemon_transport_does_not_prevent_process_exit():
    project_root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(project_root)
    script = """
import os
import threading
os.environ["DO_NOT_TRACK"] = "1"
from unstructured import telemetry
from unstructured.documents.elements import Text

entered = threading.Event()
class BlockedSession:
    trust_env = True
    def mount(self, *args, **kwargs): pass
    def get(self, *args, **kwargs):
        entered.set()
        threading.Event().wait()
    def close(self): pass

telemetry.requests.Session = BlockedSession
os.environ.pop("DO_NOT_TRACK")

def partition_text(): return [Text("ok")]
partition_text.__name__ = "partition_text"
wrapped = telemetry.partition_runtime_telemetry("txt")(partition_text)
assert wrapped()[0].text == "ok"
assert entered.wait(1)
print("exiting")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        env=env,
        text=True,
        timeout=3,
    )

    assert result.returncode == 0, result.stderr
    assert "exiting" in result.stdout


def test_all_public_entrypoints_have_the_outermost_runtime_decorator():
    project_root = Path(__file__).resolve().parent.parent
    modules = {
        "auto.py": ["partition"],
        "api.py": ["partition_via_api", "partition_multiple_via_api"],
        **{
            f"{name}.py": [f"partition_{name}"]
            for name in [
                "audio",
                "csv",
                "doc",
                "docx",
                "email",
                "epub",
                "image",
                "json",
                "md",
                "msg",
                "ndjson",
                "odt",
                "org",
                "pdf",
                "ppt",
                "pptx",
                "rst",
                "rtf",
                "text",
                "tsv",
                "xlsx",
                "xml",
            ]
        },
        "html/partition.py": ["partition_html"],
    }

    decorated: set[str] = set()
    for relative_path, function_names in modules.items():
        tree = ast.parse((project_root / "unstructured/partition" / relative_path).read_text())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name not in function_names:
                continue
            assert node.decorator_list
            outermost = node.decorator_list[0]
            assert isinstance(outermost, ast.Call)
            assert isinstance(outermost.func, ast.Name)
            assert outermost.func.id == "partition_runtime_telemetry"
            decorated.add(node.name)

    assert decorated == telemetry._PARTITIONERS
