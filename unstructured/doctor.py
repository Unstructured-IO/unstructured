"""Environment and capability diagnostics for optional dependencies and system tools."""

from __future__ import annotations

import importlib.util
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from unstructured.__version__ import __version__
from unstructured.file_utils.model import FileType
from unstructured.utils import dependency_exists

Status = Literal["ok", "missing", "warn"]

# File types that rely on LibreOffice for conversion (see partition/common/common.py).
_FILE_TYPES_NEEDING_SOFFICE: frozenset[FileType] = frozenset({FileType.DOC, FileType.PPT})


@dataclass(frozen=True)
class CapabilityResult:
    """Result of checking whether partitioning is viable for a target file type."""

    ready: bool
    """True when Python deps and required external tools for this type are satisfied."""
    messages: tuple[str, ...]
    """Human-readable issues (blocking or informational)."""


def _pip_hint_for_file_type(file_type: FileType) -> str:
    extra = file_type.extra_name
    if extra:
        return f'pip install "unstructured[{extra}]"'
    return "pip install unstructured"


def _needs_pandoc_runtime(file_type: FileType) -> bool:
    return "pypandoc" in file_type.importable_package_dependencies


def _audio_extra_import_ok() -> bool:
    return importlib.util.find_spec("whisper") is not None


def _libmagic_status() -> tuple[Status, str]:
    try:
        import magic

        _ = magic.from_buffer(b"%PDF-1.4\n", mime=True)
    except ImportError:
        return "warn", "python `magic` module not available (filetype fallback still works)"
    except Exception as exc:  # noqa: BLE001 — surface libmagic load/binary issues
        return "warn", f"libmagic not usable: {exc!s}"[:200]
    else:
        return "ok", "libmagic (python-magic) OK"


def _tool_status(name: str, on_path: bool) -> tuple[Status, str]:
    if on_path:
        return "ok", f"{name} found on PATH"
    return "missing", f"{name} not found on PATH"


def python_import_deps_ok(file_type: FileType) -> tuple[bool, list[str]]:
    """Return whether declared importable dependencies for `file_type` are importable."""
    missing: list[str] = []
    for mod in file_type.importable_package_dependencies:
        if not dependency_exists(mod):
            missing.append(mod)
    return len(missing) == 0, missing


def evaluate_file_type_capability(file_type: FileType) -> CapabilityResult:
    """Check partitioning readiness for a single :class:`FileType`."""
    if not file_type.is_partitionable:
        return CapabilityResult(
            ready=False,
            messages=(f"{file_type.name} is not partitionable.",),
        )

    ok, missing = python_import_deps_ok(file_type)
    messages: list[str] = []
    if not ok:
        messages.append(
            f"Missing Python module(s): {', '.join(missing)}. "
            f"Install with: {_pip_hint_for_file_type(file_type)}",
        )

    if _needs_pandoc_runtime(file_type) and ok and shutil.which("pandoc") is None:
        ok = False
        messages.append(
            "Pandoc executable not found on PATH (required by pypandoc). "
            "Install pandoc from https://pandoc.org/installing.html",
        )

    if file_type in _FILE_TYPES_NEEDING_SOFFICE and ok and _libreoffice_on_path() is None:
        ok = False
        messages.append(
            "soffice (LibreOffice CLI) not found on PATH. "
            "Required to convert legacy .doc / .ppt to Open XML formats.",
        )

    # Audio partitioner uses the `audio` extra (Whisper); FileType members only list empty deps.
    if file_type.extra_name == "audio":
        if not _audio_extra_import_ok():
            ok = False
            messages.append(
                "Missing audio extra (e.g. Whisper). "
                'Install with: pip install "unstructured[audio]"',
            )
        if shutil.which("ffmpeg") is None:
            ok = False
            messages.append(
                "ffmpeg not on PATH - required for Whisper audio decoding "
                "(https://ffmpeg.org/download.html).",
            )

    return CapabilityResult(ready=ok, messages=tuple(messages))


def _libreoffice_on_path() -> str | None:
    """Return ``soffice`` on PATH; matches :func:`convert_office_doc` in ``partition.common``."""
    return shutil.which("soffice")


def resolve_specifier(spec: str) -> list[FileType]:
    """Map a user string (e.g. ``pdf``, ``png``, ``image``) to :class:`FileType` members."""
    raw = spec.strip()
    if not raw:
        raise ValueError("Empty specifier")
    lower = raw.lower()

    if lower == "image":
        return [ft for ft in FileType if ft.is_partitionable and ft.extra_name == "image"]
    if lower == "audio":
        return [ft for ft in FileType if ft.is_partitionable and ft.extra_name == "audio"]

    matches: list[FileType] = []
    for ft in FileType:
        if not ft.is_partitionable:
            continue
        if ft.name.lower() == lower or ft.value == lower:
            matches.append(ft)
            continue
        if ft.partitioner_shortname and ft.partitioner_shortname.lower() == lower:
            matches.append(ft)

    if not matches:
        valid = sorted(
            {ft.value for ft in FileType if ft.is_partitionable}
            | {ft.name.lower() for ft in FileType if ft.is_partitionable}
            | {"image", "audio"},
        )
        sample = ", ".join(valid[:20])
        raise ValueError(f"Unknown file type or alias {spec!r}. Examples: {sample}...")

    # Prefer exact value/name matches over partitioner_shortname duplicates.
    exact = [ft for ft in matches if ft.value == lower or ft.name.lower() == lower]
    return exact or matches


def evaluate_specifier(spec: str) -> CapabilityResult:
    """Combine evaluation for all file types matched by :func:`resolve_specifier`."""
    targets = resolve_specifier(spec)
    if (
        len(targets) > 1
        and targets[0].extra_name in ("image", "audio")
        and all(t.extra_name == targets[0].extra_name for t in targets)
    ):
        targets = [targets[0]]
    combined_ready = True
    all_messages: list[str] = []
    for ft in targets:
        result = evaluate_file_type_capability(ft)
        if not result.ready:
            combined_ready = False
        for m in result.messages:
            all_messages.append(f"[{ft.name}] {m}")
    # De-duplicate messages while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for m in all_messages:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    return CapabilityResult(ready=combined_ready, messages=tuple(deduped))


def environment_rows() -> list[tuple[str, str, str]]:
    """Rows for the environment section: (name, status, detail)."""
    return [
        ("Python", "ok", platform.python_version()),
        ("Platform", "ok", platform.platform()),
        ("unstructured", "ok", __version__),
    ]


def system_tool_rows() -> list[tuple[str, Status, str]]:
    """Rows for optional system tools."""
    rows: list[tuple[str, Status, str]] = []
    st, detail = _libmagic_status()
    rows.append(("libmagic (MIME detection)", st, detail))

    for label, cmd in (
        ("tesseract (OCR)", "tesseract"),
        ("pandoc", "pandoc"),
        ("ffmpeg (audio/codecs)", "ffmpeg"),
    ):
        status, msg = _tool_status(label, shutil.which(cmd) is not None)
        rows.append((label, status, msg))
    lo = _libreoffice_on_path()
    rows.append(
        (
            "soffice (LibreOffice CLI)",
            "ok" if lo else "missing",
            f"found: {lo}" if lo else "not found on PATH",
        ),
    )
    return rows


def partitionable_file_type_rows() -> list[tuple[str, str, str, str]]:
    """One row per partitionable file type: type, deps OK, extra, notes."""
    out: list[tuple[str, str, str, str]] = []
    for ft in sorted(
        (m for m in FileType if m.is_partitionable),
        key=lambda x: x.name,
    ):
        py_ok, _missing = python_import_deps_ok(ft)
        deps_cell = "yes" if py_ok else "no"
        extra = ft.extra_name or "-"
        cap = evaluate_file_type_capability(ft)
        notes = " | ".join(cap.messages) if cap.messages else "-"
        out.append((ft.name, deps_cell, extra, notes))
    return out


def format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """Render a simple fixed-width table (no third-party deps)."""
    if not rows:
        return " | ".join(headers) + "\n(no rows)\n"
    col_widths = [len(h) for h in headers]
    str_rows: list[list[str]] = []
    for row in rows:
        cells = [str(c) for c in row]
        str_rows.append(cells)
        for i, cell in enumerate(cells):
            col_widths[i] = max(col_widths[i], len(cell))
    sep = "-+-".join("-" * w for w in col_widths)
    lines = [
        " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))),
        sep,
    ]
    for cells in str_rows:
        lines.append(" | ".join(cells[i].ljust(col_widths[i]) for i in range(len(headers))))
    return "\n".join(lines) + "\n"


def build_report() -> str:
    """Full diagnostic report for :command:`unstructured doctor` with no filter."""
    parts: list[str] = []
    parts.append("Environment\n")
    parts.append(format_table(("Component", "Status", "Detail"), environment_rows()))

    parts.append("System tools (optional but commonly needed)\n")
    sys_rows = system_tool_rows()
    parts.append(format_table(("Tool", "Status", "Detail"), sys_rows))

    parts.append("Partitionable file types (Python extras)\n")
    p_rows = partitionable_file_type_rows()
    parts.append(
        format_table(
            ("File type", "Python deps OK", "pip extra", "Notes"),
            [tuple(r) for r in p_rows],
        ),
    )
    return "".join(parts)


def file_path_to_capability(path: str | Path) -> CapabilityResult:
    """Infer file type from ``path`` and evaluate capability."""
    p = Path(path)
    if not p.is_file():
        return CapabilityResult(ready=False, messages=(f"Not a file or not found: {p}",))

    from unstructured.file_utils.filetype import detect_filetype

    ft = detect_filetype(file_path=str(p.resolve()))
    if not ft.is_partitionable:
        return CapabilityResult(
            ready=False,
            messages=(f"Detected type {ft.name} is not partitionable.",),
        )
    return evaluate_file_type_capability(ft)
