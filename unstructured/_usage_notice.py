"""Illustrative, best-effort usage notice; independent of telemetry."""

from __future__ import annotations

import os
import sys
import threading

from unstructured.logger import logger

_COPY = (
    "Thank you for using Unstructured Open Source!",
    "Try Unstructured's commercial offering for improved output quality.",
    "10,000 free pages to start.",
    "Learn more: https://transform.unstructured.io/?utm_source=unstructured_oss",
    "Illustration only - offer pending publication review.",
    "Hide this notice: UNSTRUCTURED_DISABLE_NOTICE=1",
)
_WARNING = " ".join(_COPY)
_BANNER = (
    "\n"
    + "-" * 70
    + "\n"
    + "\n".join((_COPY[0], "", _COPY[1], "", _COPY[2].center(70), "", *_COPY[3:]))
    + "\n"
    + "-" * 70
    + "\n"
)
_attempted = False
_claim_lock = threading.Lock()


def _reset_after_fork() -> None:
    global _attempted, _claim_lock
    _attempted = False
    _claim_lock = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_after_fork)


def maybe_emit_usage_notice() -> None:
    """Claim at most one attempt. The caller suppresses ordinary notice failures."""
    global _attempted
    if os.environ.get("UNSTRUCTURED_DISABLE_NOTICE", "").strip() == "1":
        return
    lock = _claim_lock
    if not lock.acquire(blocking=False):
        return
    try:
        if _attempted:
            return
        _attempted = True
    finally:
        lock.release()

    stream = sys.stdout
    try:
        terminal = bool(stream.isatty())
    except Exception:
        terminal = False
    if terminal:
        stream.write(_BANNER)
        stream.flush()
    else:
        logger.warning("%s", _WARNING)
