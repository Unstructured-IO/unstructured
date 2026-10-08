"""Focused routing, ownership, failure, and lifecycle tests for the usage notice."""

import io
import logging
import os
import subprocess
import sys
import threading
from unittest.mock import Mock

import pytest

from unstructured import _usage_notice as notice
from unstructured import telemetry


@pytest.fixture(autouse=True)
def isolated_notice(monkeypatch):
    notice._reset_after_fork()
    monkeypatch.delenv("UNSTRUCTURED_DISABLE_NOTICE", raising=False)
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    yield
    notice._reset_after_fork()


def wrapped(body=lambda: "result"):
    return telemetry.partition_runtime_telemetry()(body)


def test_terminal_once(monkeypatch):
    stream = Mock()
    stream.isatty.return_value = True
    warning = Mock()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(notice.logger, "warning", warning)
    call = wrapped()
    assert call() == call() == "result"
    stream.write.assert_called_once_with(notice._BANNER)
    stream.flush.assert_called_once_with()
    warning.assert_not_called()
    assert notice._BANNER.isascii()
    for text in notice._COPY:
        assert text in notice._BANNER


@pytest.mark.parametrize(
    "stream", [None, io.StringIO(), object(), Mock(isatty=Mock(side_effect=OSError))]
)
def test_unconfirmed_stdout_logs_once(monkeypatch, stream):
    warning = Mock()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(notice.logger, "warning", warning)
    assert wrapped()() == "result"
    wrapped()()
    warning.assert_called_once_with("%s", notice._WARNING)
    assert "\n" not in notice._WARNING
    for text in notice._COPY:
        assert text in notice._WARNING
    if isinstance(stream, io.StringIO):
        assert stream.getvalue() == ""


@pytest.mark.parametrize(
    ("value", "disabled"), [("1", True), (" 1 ", True), ("0", False), ("true", False), ("", False)]
)
def test_disable_at_use_time(monkeypatch, value, disabled):
    warning = Mock()
    monkeypatch.setattr(notice.logger, "warning", warning)
    monkeypatch.setenv("UNSTRUCTURED_DISABLE_NOTICE", value)
    wrapped()()
    assert warning.call_count == (0 if disabled else 1)
    monkeypatch.delenv("UNSTRUCTURED_DISABLE_NOTICE")
    wrapped()()
    assert warning.call_count == 1


@pytest.mark.parametrize("failure", ["write", "flush", "logger"])
def test_notice_failure_preserves_results_and_exceptions(monkeypatch, failure):
    stream = Mock()
    stream.isatty.return_value = failure != "logger"
    warning = Mock()
    if failure == "logger":
        warning.side_effect = RuntimeError("sink")
    else:
        getattr(stream, failure).side_effect = RuntimeError("sink")
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(notice.logger, "warning", warning)
    result = object()
    calls = []

    def body(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    assert wrapped(body)(3, key="value") is result
    assert calls == [((3,), {"key": "value"})]
    sentinel = ValueError("original")

    def fail():
        raise sentinel

    with pytest.raises(ValueError, match="original") as exc:
        wrapped(fail)()
    assert exc.value is sentinel
    if failure != "logger":
        warning.assert_not_called()
    assert stream.write.call_count + warning.call_count == 1


@pytest.mark.parametrize("optout", [True, False, "raises"])
def test_notice_independent_of_telemetry(monkeypatch, optout):
    warning = Mock()
    schedule = Mock()
    monkeypatch.setattr(notice.logger, "warning", warning)
    monkeypatch.setattr(telemetry, "_schedule_delivery", schedule)
    monkeypatch.setattr(
        telemetry,
        "_telemetry_opt_out",
        Mock(
            return_value=optout,
            side_effect=RuntimeError() if optout == "raises" else None,
        ),
    )
    wrapped()()
    assert warning.call_count == 1
    assert schedule.call_count == (1 if optout is False else 0)
    notice._reset_after_fork()
    monkeypatch.setenv("UNSTRUCTURED_DISABLE_NOTICE", "1")
    wrapped()()
    assert warning.call_count == 1
    assert schedule.call_count == (2 if optout is False else 0)


def test_concurrent_callers_and_reentry_do_not_wait_for_sink(monkeypatch):
    entered, release, body_entered = threading.Event(), threading.Event(), threading.Event()
    barrier = threading.Barrier(8)
    errors = []
    count = []

    def sink(*args):
        count.append(1)
        assert wrapped()() == "result"  # Reentry must not claim or deadlock.
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(notice.logger, "warning", sink)

    def caller():
        try:
            barrier.wait(timeout=5)
            wrapped(lambda: body_entered.set())()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=caller) for _ in range(8)]
    for thread in threads:
        thread.start()
    try:
        assert entered.wait(5)
        assert body_entered.wait(5)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors
    assert len(count) == 1


def test_logger_configuration_is_owned_by_application(monkeypatch):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = notice.logger
    monkeypatch.setattr(logger, "handlers", [handler])
    monkeypatch.setattr(logger, "propagate", False)
    logger.setLevel(logging.WARNING)
    wrapped()()
    assert stream.getvalue().count("10,000 free pages to start.") == 1
    assert logger.handlers == [handler]
    assert logger.level == logging.WARNING
    notice._reset_after_fork()
    monkeypatch.setenv("UNSTRUCTURED_DISABLE_NOTICE", "1")
    wrapped()()
    assert stream.getvalue().count("10,000 free pages to start.") == 1
    monkeypatch.delenv("UNSTRUCTURED_DISABLE_NOTICE")
    logger.setLevel(logging.ERROR)
    wrapped()()
    logger.setLevel(logging.WARNING)
    wrapped()()
    assert stream.getvalue().count("10,000 free pages to start.") == 1


@pytest.mark.parametrize("filter_raises", [False, True])
def test_logger_filter_failure_or_suppression_consumes_attempt(monkeypatch, filter_raises):
    filter_ = Mock()
    filter_.filter.side_effect = RuntimeError("filter") if filter_raises else None
    filter_.filter.return_value = False
    monkeypatch.setattr(notice.logger, "filters", [filter_])
    monkeypatch.setattr(notice.logger, "level", logging.WARNING)
    wrapped()()
    wrapped()()
    assert filter_.filter.call_count == 1


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires Python fork")
def test_fork_resets_attempt_and_inherited_locked_claim():
    script = """
import os
from unstructured import _usage_notice as n
from unstructured.telemetry import partition_runtime_telemetry
call = partition_runtime_telemetry()(lambda: None)
call(); call()
n._claim_lock.acquire()
pid = os.fork()
if pid == 0:
    call(); call()
    os._exit(0)
n._claim_lock.release()
_, status = os.waitpid(pid, 0)
assert status == 0
call()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "DO_NOT_TRACK": "1"},
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert result.stdout == ""
    assert result.stderr.count("10,000 free pages to start.") == 2


def test_public_entrypoints_unchanged_and_empty_call(caplog, monkeypatch):
    from unstructured.partition.auto import partition
    from unstructured.partition.text import partition_text

    sample = "This is a local usage notice demonstration sentence."
    options = {"paragraph_grouper": False, "languages": ["eng"]}
    assert partition_text(text="", **options) == []
    enabled = partition(file=io.BytesIO(sample.encode()), content_type="text/plain", **options)
    direct = partition_text(text=sample, **options)
    monkeypatch.setenv("UNSTRUCTURED_DISABLE_NOTICE", "1")
    disabled = partition_text(text=sample, **options)

    def project(elements):
        return [(e.category, e.text) for e in elements]

    assert project(enabled) == project(direct) == project(disabled)
    assert caplog.text.count("10,000 free pages to start.") == 1


@pytest.mark.parametrize("flag", ["DO_NOT_TRACK", "SCARF_NO_ANALYTICS"])
def test_each_telemetry_disable_flag_keeps_notice(monkeypatch, flag):
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.setenv(flag, "1")
    warning = Mock()
    monkeypatch.setattr(notice.logger, "warning", warning)
    wrapped()()
    warning.assert_called_once_with("%s", notice._WARNING)


def test_stream_selection_ignores_stdin_and_stderr(monkeypatch):
    stream = Mock()
    stream.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    wrapped()()
    stream.write.assert_called_once_with(notice._BANNER)
    notice._reset_after_fork()
    redirected = io.StringIO()
    monkeypatch.setattr(sys, "stdout", redirected)
    monkeypatch.setattr(sys, "stderr", stream)
    warning = Mock()
    monkeypatch.setattr(notice.logger, "warning", warning)
    wrapped()()
    assert redirected.getvalue() == ""
    warning.assert_called_once()


def test_first_failed_invocation_consumes_attempt(monkeypatch):
    warning = Mock()
    monkeypatch.setattr(notice.logger, "warning", warning)

    def fail():
        raise ValueError("partition failure")

    with pytest.raises(ValueError, match="partition failure"):
        wrapped(fail)()
    wrapped()()
    warning.assert_called_once()


def test_base_exception_is_not_suppressed(monkeypatch):
    monkeypatch.setattr(notice.logger, "warning", Mock(side_effect=KeyboardInterrupt))
    body = Mock()
    with pytest.raises(KeyboardInterrupt):
        wrapped(lambda: body())()
    body.assert_not_called()


def test_fresh_spawn_and_import_silence(tmp_path):
    script = tmp_path / "spawn_notice.py"
    script.write_text("""
import multiprocessing
from unstructured.telemetry import partition_runtime_telemetry

def run():
    call = partition_runtime_telemetry()(lambda: None)
    call(); call()

if __name__ == "__main__":
    run()
    worker = multiprocessing.get_context("spawn").Process(target=run)
    worker.start()
    worker.join(10)
    assert not worker.is_alive()
    assert worker.exitcode == 0
""")
    env = {**os.environ, "DO_NOT_TRACK": "1", "PYTHONPATH": os.getcwd()}
    result = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    assert result.stdout == ""
    assert result.stderr.count("10,000 free pages to start.") == 2
    result = subprocess.run(
        [sys.executable, "-c", "import unstructured.partition.text"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert result.stdout == ""
    assert result.stderr == ""
