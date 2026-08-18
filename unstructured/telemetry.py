"""Best-effort startup and partition-runtime telemetry."""

from __future__ import annotations

import functools
import inspect
import os
import platform
import threading
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, ParamSpec, TypeVar

import requests
from requests.adapters import HTTPAdapter

from unstructured.__version__ import __version__
from unstructured.utils import _telemetry_opt_out, scarf_analytics

_P = ParamSpec("_P")
_R = TypeVar("_R")

_ENDPOINT = "https://packages.unstructured.io/v1/partition"
_HTTP_TIMEOUT = (0.2, 0.2)
_DELIVERY_SLOT = threading.BoundedSemaphore(1)
_PROCESS_ID = os.getpid()

_PARTITIONERS = {
    "partition",
    "partition_audio",
    "partition_csv",
    "partition_doc",
    "partition_docx",
    "partition_email",
    "partition_epub",
    "partition_html",
    "partition_image",
    "partition_json",
    "partition_md",
    "partition_msg",
    "partition_ndjson",
    "partition_odt",
    "partition_org",
    "partition_pdf",
    "partition_ppt",
    "partition_pptx",
    "partition_rst",
    "partition_rtf",
    "partition_text",
    "partition_tsv",
    "partition_via_api",
    "partition_multiple_via_api",
    "partition_xlsx",
    "partition_xml",
}
_DOCUMENT_TYPES = {
    "bmp",
    "csv",
    "doc",
    "docx",
    "eml",
    "epub",
    "flac",
    "heic",
    "html",
    "jpg",
    "json",
    "m4a",
    "md",
    "mp3",
    "msg",
    "ndjson",
    "odt",
    "ogg",
    "opus",
    "org",
    "pdf",
    "png",
    "ppt",
    "pptx",
    "rst",
    "rtf",
    "tiff",
    "tsv",
    "txt",
    "wav",
    "webm",
    "xls",
    "xlsx",
    "xml",
    "zip",
    "empty",
    "unknown",
    "other",
}
_IMAGE_TYPES = {"bmp", "heic", "jpg", "png", "tiff"}
_LOCAL_TABLE_STRUCTURE_PARTITIONERS = {
    "partition_csv",
    "partition_docx",
    "partition_html",
    "partition_pptx",
    "partition_tsv",
    "partition_xlsx",
}


@dataclass
class _Invocation:
    partitioner: str
    document_type: str | None
    strategy_requested: str
    strategy_used: str
    chunking_strategy: str
    ocr_used: bool = False
    table_extraction: bool = False
    nested_local_table_results: list[Any] = field(default_factory=list)


_CURRENT_INVOCATION: ContextVar[_Invocation | None] = ContextVar(
    "partition_telemetry_invocation", default=None
)


def _reset_process_state() -> None:
    """Reset inherited thread/context state in a forked child."""
    global _CURRENT_INVOCATION, _DELIVERY_SLOT, _PROCESS_ID
    _DELIVERY_SLOT = threading.BoundedSemaphore(1)
    _CURRENT_INVOCATION = ContextVar("partition_telemetry_invocation", default=None)
    _PROCESS_ID = os.getpid()


def _ensure_process_state() -> None:
    if os.getpid() != _PROCESS_ID:
        _reset_process_state()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_process_state)


def init_telemetry() -> None:
    """Run the library-load analytics ping unless opted out. Best-effort and non-fatal."""
    scarf_analytics()


def partition_runtime_telemetry(
    document_type: str | None = None,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Decorate a public partition entrypoint with one outermost runtime event."""

    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        signature = inspect.signature(func)
        partitioner = func.__name__ if func.__name__ in _PARTITIONERS else "other"

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            # Opt-out is checked before argument inspection, context creation, or delivery work.
            try:
                opted_out = _telemetry_opt_out()
            except Exception:
                return func(*args, **kwargs)
            if opted_out:
                return func(*args, **kwargs)

            try:
                _ensure_process_state()
                active_invocation = _CURRENT_INVOCATION.get()
            except Exception:
                return func(*args, **kwargs)

            # Public partitioners routinely dispatch to other public partitioners internally.
            # Only the outermost call owns an event; nested calls can still record execution facts.
            # The current internal dispatch graph is synchronous; ContextVar state does not cross
            # into a newly-created thread, so any future threaded dispatch must propagate context.
            if active_invocation is not None:
                result = func(*args, **kwargs)
                if partitioner in _LOCAL_TABLE_STRUCTURE_PARTITIONERS:
                    with suppress(Exception):
                        active_invocation.nested_local_table_results.append(result)
                return result

            try:
                invocation = _new_invocation(partitioner)
                token = _CURRENT_INVOCATION.set(invocation)
            except Exception:
                return func(*args, **kwargs)
            try:
                with suppress(Exception):
                    _prepare_invocation(invocation, signature, document_type, args, kwargs)
                try:
                    result = func(*args, **kwargs)
                except BaseException:
                    with suppress(Exception):
                        _finish_error(invocation)
                    raise
                else:
                    with suppress(Exception):
                        _finish_success(invocation, result)
                    return result
            finally:
                with suppress(Exception):
                    _CURRENT_INVOCATION.reset(token)

        return wrapper

    return decorator


def set_partition_document_type(document_type: Any) -> None:
    """Record a type already resolved by normal partition processing."""
    if document_type is None:
        return
    with suppress(Exception):
        _ensure_process_state()
        invocation = _CURRENT_INVOCATION.get()
        if (
            invocation is not None
            and invocation.document_type is None
            and invocation.partitioner
            in {
                "partition",
                "partition_audio",
                "partition_image",
            }
        ):
            invocation.document_type = _normalize_document_type(document_type)
            if invocation.document_type not in _IMAGE_TYPES | {"pdf"}:
                invocation.strategy_used = "not_applicable"


def set_partition_document_type_from_mime(mime_type: str | None) -> None:
    """Record a MIME type already resolved by processing, without forwarding its raw value."""
    invocation = _CURRENT_INVOCATION.get()
    if invocation is None:
        return
    try:
        from unstructured.file_utils.model import FileType

        file_type = FileType.from_mime_type(mime_type)
        if file_type is not None:
            set_partition_document_type(file_type)
    except Exception:
        pass


def set_partition_strategy_used(strategy: Any) -> None:
    """Record the strategy selected by normal PDF/image dispatch."""
    with suppress(Exception):
        _ensure_process_state()
        invocation = _CURRENT_INVOCATION.get()
        if invocation is not None and (
            invocation.partitioner in {"partition_image", "partition_pdf"}
            or (
                invocation.partitioner == "partition"
                and invocation.document_type in _IMAGE_TYPES | {"pdf"}
            )
        ):
            value = str(strategy)
            invocation.strategy_used = (
                value if value in {"fast", "hi_res", "ocr_only"} else "unknown"
            )


def mark_partition_ocr_used() -> None:
    """Record that an OCR engine is about to be invoked."""
    with suppress(Exception):
        _ensure_process_state()
        invocation = _CURRENT_INVOCATION.get()
        if invocation is not None:
            invocation.ocr_used = True


def mark_partition_table_extraction() -> None:
    """Record that a table-structure model is about to be invoked."""
    with suppress(Exception):
        _ensure_process_state()
        invocation = _CURRENT_INVOCATION.get()
        if invocation is not None:
            invocation.table_extraction = True


def _new_invocation(partitioner: str) -> _Invocation:
    strategy_used = (
        "unknown"
        if partitioner
        in {
            "partition",
            "partition_image",
            "partition_pdf",
            "partition_via_api",
            "partition_multiple_via_api",
        }
        else "not_applicable"
    )
    return _Invocation(
        partitioner=partitioner,
        document_type=None,
        strategy_requested="not_applicable",
        strategy_used=strategy_used,
        chunking_strategy="none",
    )


def _prepare_invocation(
    invocation: _Invocation,
    signature: inspect.Signature,
    document_type: str | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    if document_type:
        invocation.document_type = _normalize_document_type(document_type)
    try:
        call_args = dict(signature.bind_partial(*args, **kwargs).arguments)
    except Exception:
        call_args = kwargs

    requested = (
        _get_call_argument(signature, call_args, "strategy", "auto")
        if invocation.partitioner in {"partition", "partition_image", "partition_pdf"}
        else "not_applicable"
    )
    if invocation.partitioner in {"partition_via_api", "partition_multiple_via_api"}:
        requested = _get_call_argument(signature, call_args, "strategy", "auto")
    requested = str(requested) if requested is not None else "not_applicable"
    if requested not in {"auto", "fast", "hi_res", "ocr_only", "not_applicable"}:
        requested = "other"

    chunking = _get_call_argument(signature, call_args, "chunking_strategy", None)
    chunking = "none" if chunking is None else str(chunking)
    if chunking not in {"none", "basic", "by_title"}:
        chunking = "other"

    invocation.strategy_requested = requested
    invocation.chunking_strategy = chunking


def _get_call_argument(
    signature: inspect.Signature,
    call_args: dict[str, Any],
    name: str,
    default: Any,
) -> Any:
    if name in call_args:
        return call_args[name]
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            extras = call_args.get(parameter.name)
            if isinstance(extras, dict) and name in extras:
                return extras[name]
    default_parameter = signature.parameters.get(name)
    if default_parameter is not None and default_parameter.default is not inspect.Parameter.empty:
        return default_parameter.default
    return default


def _finish_error(invocation: _Invocation) -> None:
    def build_params() -> dict[str, Any]:
        params = _base_params(invocation, "error")
        if invocation.document_type is not None:
            params["document_type"] = invocation.document_type
        return params

    _schedule_delivery(build_params)


def _finish_success(invocation: _Invocation, result: Any) -> None:
    documents = result if invocation.partitioner == "partition_multiple_via_api" else [result]

    def build_params() -> dict[str, Any]:
        inferred_type, counts, has_embeddings, has_table_structure = _summarize_elements(documents)
        document_type = invocation.document_type or inferred_type or "unknown"
        table_extraction = (
            invocation.table_extraction
            or (
                invocation.partitioner in _LOCAL_TABLE_STRUCTURE_PARTITIONERS
                and has_table_structure
            )
            or any(
                _has_structured_table(result) for result in invocation.nested_local_table_results
            )
        )
        params = _base_params(invocation, "success")
        params.update(
            {
                "document_type": document_type,
                "strategy_requested": invocation.strategy_requested,
                "strategy_used": invocation.strategy_used,
                "table_extraction": str(table_extraction).lower(),
                "ocr_used": str(invocation.ocr_used).lower(),
                "chunking_strategy": invocation.chunking_strategy,
                "has_embeddings": str(has_embeddings).lower(),
                "num_documents": len(documents),
                **counts,
            }
        )
        return params

    _schedule_delivery(build_params)


def _base_params(invocation: _Invocation, outcome: str) -> dict[str, Any]:
    system = platform.system()
    machine = platform.machine().lower()
    return {
        "schema_version": 1,
        "version": __version__,
        "platform": system if system in {"Linux", "Darwin", "Windows"} else "Other",
        "python": f"{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}",
        "arch": machine if machine in {"x86_64", "amd64", "arm64", "aarch64"} else "other",
        "partitioner": invocation.partitioner,
        "outcome": outcome,
    }


def _normalize_document_type(value: Any) -> str:
    raw = getattr(value, "value", value)
    normalized = str(raw).lower().lstrip(".")
    if normalized == "jpeg":
        normalized = "jpg"
    if normalized == "heif":
        normalized = "heic"
    if normalized == "unk":
        normalized = "unknown"
    if normalized in _DOCUMENT_TYPES:
        return normalized
    return "other"


def _summarize_elements(
    documents: Any,
) -> tuple[str | None, dict[str, int], bool, bool]:
    from unstructured.documents.elements import (
        CompositeElement,
        Footer,
        Header,
        Image,
        ListItem,
        NarrativeText,
        Table,
        TableChunk,
        Title,
    )
    from unstructured.file_utils.model import FileType

    categories: tuple[tuple[str, Any], ...] = (
        ("num_titles", Title),
        ("num_narrative_text", NarrativeText),
        ("num_list_items", ListItem),
        ("num_tables", (TableChunk, Table)),
        ("num_images", Image),
        ("num_headers", Header),
        ("num_footers", Footer),
        ("num_composite_elements", CompositeElement),
    )
    counts = {name: 0 for name, _ in categories}
    document_types: set[str] = set()
    other = 0
    num_elements = 0
    has_embeddings = False
    has_table_structure = False
    for document in documents:
        for element in document:
            num_elements += 1
            metadata = getattr(element, "metadata", None)
            mime_type = getattr(metadata, "filetype", None)
            file_type = FileType.from_mime_type(mime_type)
            if file_type is not None:
                document_types.add(_normalize_document_type(file_type.value))
            has_embeddings = has_embeddings or bool(getattr(element, "embeddings", None))
            has_table_structure = has_table_structure or (
                isinstance(element, Table) and getattr(metadata, "text_as_html", None) is not None
            )
            for name, cls in categories:
                if isinstance(element, cls):
                    counts[name] += 1
                    break
            else:
                other += 1
    assert sum(counts.values()) + other == num_elements
    document_type = (
        None
        if not document_types
        else next(iter(document_types))
        if len(document_types) == 1
        else "other"
    )
    return (
        document_type,
        {"num_elements": num_elements, **counts, "num_other_elements": other},
        has_embeddings,
        has_table_structure,
    )


def _has_structured_table(result: Any) -> bool:
    """Whether a concrete local child result contains table structure."""
    if not isinstance(result, (list, tuple)):
        return False
    from unstructured.documents.elements import Table

    return any(
        isinstance(element, Table)
        and getattr(getattr(element, "metadata", None), "text_as_html", None) is not None
        for element in result
    )


def _schedule_delivery(build_params: Callable[[], dict[str, Any]]) -> None:
    # No queue: one stalled transport occupies the sole slot and all later events are dropped.
    _ensure_process_state()
    if not _DELIVERY_SLOT.acquire(blocking=False):
        return
    try:
        params = build_params()
        threading.Thread(
            target=_deliver,
            args=(params,),
            name="unstructured-telemetry",
            daemon=True,
        ).start()
    except Exception:
        _DELIVERY_SLOT.release()
    except BaseException:
        _DELIVERY_SLOT.release()
        raise


def _deliver(params: dict[str, Any]) -> None:
    response: requests.Response | None = None
    session: requests.Session | None = None
    try:
        session = requests.Session()
        session.trust_env = False
        session.mount("http://", HTTPAdapter(max_retries=0))
        session.mount("https://", HTTPAdapter(max_retries=0))
        response = session.get(
            _ENDPOINT,
            params=params,
            timeout=_HTTP_TIMEOUT,
            allow_redirects=False,
            stream=True,
        )
    except BaseException:
        pass
    finally:
        if response is not None:
            with suppress(BaseException):
                response.close()
        if session is not None:
            with suppress(BaseException):
                session.close()
        _DELIVERY_SLOT.release()
