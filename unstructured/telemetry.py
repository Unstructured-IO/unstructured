"""Telemetry initializer. Called once at package startup from unstructured/__init__.py."""

from unstructured.utils import scarf_analytics


def init_telemetry() -> None:
    """Run the library-load analytics ping unless opted out. Best-effort and non-fatal."""
    scarf_analytics()
