"""Tests for :mod:`unstructured.cli` and :mod:`unstructured.doctor`."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

from unstructured.cli import _cmd_doctor, main
from unstructured.doctor import (
    _libmagic_status,
    _needs_pandoc_runtime,
    _pip_hint_for_file_type,
    _tool_status,
    build_report,
    environment_rows,
    evaluate_file_type_capability,
    evaluate_specifier,
    file_path_to_capability,
    format_table,
    python_import_deps_ok,
    resolve_specifier,
    system_tool_rows,
)
from unstructured.file_utils.model import FileType


def test_resolve_specifier_pdf() -> None:
    fts = resolve_specifier("pdf")
    assert fts == [FileType.PDF]


def test_resolve_specifier_jpg_exact() -> None:
    assert resolve_specifier("jpg") == [FileType.JPG]


def test_resolve_specifier_image_family() -> None:
    fts = resolve_specifier("image")
    assert len(fts) >= 1
    assert all(ft.extra_name == "image" for ft in fts)


def test_resolve_specifier_audio_family() -> None:
    fts = resolve_specifier("audio")
    assert len(fts) >= 1
    assert all(ft.extra_name == "audio" for ft in fts)


def test_resolve_specifier_email_partitioner_shortname() -> None:
    assert FileType.EML in resolve_specifier("email")


def test_resolve_specifier_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        resolve_specifier("not-a-real-type-xyz")


def test_resolve_specifier_empty() -> None:
    with pytest.raises(ValueError, match="Empty"):
        resolve_specifier("   ")


def test_evaluate_specifier_dedupes_image_family() -> None:
    with mock.patch("unstructured.doctor.evaluate_file_type_capability") as ev:
        ev.return_value = mock.Mock(ready=True, messages=())
        r = evaluate_specifier("image")
        assert r.ready is True
        assert ev.call_count == 1


def test_evaluate_specifier_multiple_targets() -> None:
    def _cap(ready: bool, *msgs: str) -> mock.Mock:
        m = mock.Mock()
        m.ready = ready
        m.messages = tuple(msgs)
        return m

    with (
        mock.patch(
            "unstructured.doctor.resolve_specifier",
            return_value=[FileType.PDF, FileType.CSV],
        ),
        mock.patch(
            "unstructured.doctor.evaluate_file_type_capability",
            side_effect=[_cap(False, "a"), _cap(True)],
        ),
    ):
        r = evaluate_specifier("x")
        assert r.ready is False
        assert "[PDF] a" in r.messages


def test_evaluate_specifier_dedupes_repeated_message_lines() -> None:
    with (
        mock.patch("unstructured.doctor.resolve_specifier", return_value=[FileType.PDF]),
        mock.patch(
            "unstructured.doctor.evaluate_file_type_capability",
            return_value=mock.Mock(ready=False, messages=("dup", "dup")),
        ),
    ):
        r = evaluate_specifier("pdf")
        assert r.messages.count("[PDF] dup") == 1


def test_main_doctor_invocation() -> None:
    with mock.patch("unstructured.cli._cmd_doctor", return_value=0) as m:
        assert main(["doctor"]) == 0
        m.assert_called_once_with([])


def test_main_no_argv_reads_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["unstructured", "doctor", "--for", "txt"])
    with mock.patch("unstructured.cli._cmd_doctor", return_value=0) as m:
        assert main(None) == 0
        m.assert_called_once_with(["--for", "txt"])


def test_main_unknown() -> None:
    assert main(["nope"]) == 2


def test_main_help_returns_zero() -> None:
    assert main(["--help"]) == 0


def test_cmd_doctor_for_missing_dep_exit_code() -> None:
    with mock.patch(
        "unstructured.doctor.evaluate_specifier",
        return_value=mock.Mock(ready=False, messages=("missing",)),
    ):
        assert _cmd_doctor(["--for", "pdf"]) == 1


def test_cmd_doctor_for_ok() -> None:
    with mock.patch(
        "unstructured.doctor.evaluate_specifier",
        return_value=mock.Mock(ready=True, messages=()),
    ):
        assert _cmd_doctor(["--for", "pdf"]) == 0


def test_cmd_doctor_for_prints_messages(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch(
        "unstructured.doctor.evaluate_specifier",
        return_value=mock.Mock(ready=True, messages=("note",)),
    ):
        assert _cmd_doctor(["--for", "pdf"]) == 0
    assert "note" in capsys.readouterr().out


def test_cmd_doctor_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pdf"
    assert _cmd_doctor(["--file", str(missing)]) == 1


def test_cmd_doctor_file_txt_ok(tmp_path: Path) -> None:
    pytest.importorskip("olefile")
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    assert _cmd_doctor(["--file", str(f)]) == 0


def test_cmd_doctor_file_prints_messages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    f = tmp_path / "b.txt"
    f.write_text("x", encoding="utf-8")
    with mock.patch(
        "unstructured.doctor.file_path_to_capability",
        return_value=mock.Mock(ready=True, messages=("hi",)),
    ):
        assert _cmd_doctor(["--file", str(f)]) == 0
    assert "hi" in capsys.readouterr().out


def test_cmd_doctor_for_and_file_mutually_exclusive_returns_2() -> None:
    assert _cmd_doctor(["--for", "pdf", "--file", "any.pdf"]) == 2


def test_cmd_doctor_invalid_for_returns_2() -> None:
    assert _cmd_doctor(["--for", "not-a-real-type-xyz"]) == 2


def test_cmd_doctor_default_prints_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert _cmd_doctor([]) == 0
    out = capsys.readouterr().out
    assert "Environment" in out
    assert "Partitionable file types" in out


def test_evaluate_doc_requires_soffice_when_deps_ok() -> None:
    with mock.patch("unstructured.doctor.python_import_deps_ok", return_value=(True, [])):
        with mock.patch("unstructured.doctor._libreoffice_on_path", return_value=None):
            r = evaluate_file_type_capability(FileType.DOC)
            assert r.ready is False
            assert "soffice" in "".join(r.messages).lower()


def test_evaluate_epub_requires_pandoc_binary_when_python_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with mock.patch("unstructured.doctor.python_import_deps_ok", return_value=(True, [])):

        def _which(cmd: str) -> str | None:
            if cmd == "pandoc":
                return None
            return "/fake/bin/" + cmd

        monkeypatch.setattr("unstructured.doctor.shutil.which", _which)
        r = evaluate_file_type_capability(FileType.EPUB)
        assert r.ready is False
        assert "Pandoc" in "".join(r.messages)


def test_evaluate_zip_not_partitionable() -> None:
    r = evaluate_file_type_capability(FileType.ZIP)
    assert r.ready is False
    assert "not partitionable" in r.messages[0]


def test_evaluate_html_no_extra() -> None:
    r = evaluate_file_type_capability(FileType.HTML)
    assert r.ready is True
    assert not r.messages


def test_evaluate_audio_not_ready_without_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    real_which = shutil.which

    def _which(cmd: str) -> str | None:
        if cmd == "ffmpeg":
            return None
        return real_which(cmd)

    monkeypatch.setattr("unstructured.doctor.shutil.which", _which)
    with mock.patch("unstructured.doctor._audio_extra_import_ok", return_value=True):
        r = evaluate_file_type_capability(FileType.MP3)
    assert r.ready is False
    assert "ffmpeg" in " ".join(r.messages).lower()


def test_python_import_deps_ok_returns_missing() -> None:
    ok, missing = python_import_deps_ok(FileType.PDF)
    assert isinstance(ok, bool)
    assert isinstance(missing, list)


def test_format_table_empty_rows() -> None:
    out = format_table(("A", "B"), [])
    assert "(no rows)" in out


def test_format_table_with_rows() -> None:
    out = format_table(("Col",), [("val",)])
    assert "Col" in out
    assert "val" in out


def test_environment_rows() -> None:
    rows = environment_rows()
    labels = [r[0] for r in rows]
    assert "Python" in labels
    assert "unstructured" in labels


def test_system_tool_rows_shape() -> None:
    rows = system_tool_rows()
    assert len(rows) >= 5
    assert all(len(r) == 3 for r in rows)


def test_tool_status_branches() -> None:
    assert _tool_status("x", True)[0] == "ok"
    assert _tool_status("x", False)[0] == "missing"


def test_pip_hint_for_file_type() -> None:
    assert "pdf" in _pip_hint_for_file_type(FileType.PDF)
    assert _pip_hint_for_file_type(FileType.HTML) == "pip install unstructured"


def test_needs_pandoc_runtime() -> None:
    assert _needs_pandoc_runtime(FileType.EPUB) is True
    assert _needs_pandoc_runtime(FileType.HTML) is False


def test_build_report_smoke() -> None:
    report = build_report()
    assert "Environment" in report
    assert "System tools" in report
    assert "Partitionable file types" in report


def test_file_path_to_capability_txt(tmp_path: Path) -> None:
    pytest.importorskip("olefile")
    f = tmp_path / "n.txt"
    f.write_text("x", encoding="utf-8")
    r = file_path_to_capability(f)
    assert r.ready is True


def test_file_path_to_capability_zip(tmp_path: Path) -> None:
    pytest.importorskip("olefile")
    zp = tmp_path / "empty.zip"
    with zipfile.ZipFile(zp, "w"):
        pass
    r = file_path_to_capability(zp)
    assert r.ready is False
    assert "not partitionable" in r.messages[0]


def test_file_path_to_capability_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.txt"
    r = file_path_to_capability(missing)
    assert r.ready is False
    assert "Not a file" in r.messages[0]


def test_libmagic_status_ok_with_mocked_magic(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = mock.MagicMock()
    fake.from_buffer = mock.MagicMock(return_value="application/pdf")
    monkeypatch.setitem(sys.modules, "magic", fake)
    st, msg = _libmagic_status()
    assert st == "ok"
    assert "OK" in msg or "ok" in msg


def test_libmagic_status_warn_when_from_buffer_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = mock.MagicMock()
    fake.from_buffer = mock.MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setitem(sys.modules, "magic", fake)
    st, msg = _libmagic_status()
    assert st == "warn"
    assert "libmagic" in msg.lower()


def test_libmagic_status_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _imp(name: str, *args, **kwargs):
        if name == "magic":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _imp)
    st, msg = _libmagic_status()
    assert st == "warn"
    assert "magic" in msg.lower() or "fallback" in msg.lower()
