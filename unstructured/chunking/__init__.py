"""Chunking module initializer.

Provides the the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

from typing_extensions import ParamSpec

from unstructured.chunking.base import CHUNK_MAX_CHARS_DEFAULT, CHUNK_MULTI_PAGE_DEFAULT
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element

_P = ParamSpec("_P")


def add_chunking_strategy() -> Callable[[Callable[_P, list[Element]]], Callable[_P, list[Element]]]:
    """Decorator for chunking text.

    Chunks the element sequence produced by the partitioner it decorates when a `chunking_strategy`
    argument is present in the partitioner call and it names an available chunking strategy.
    """

    def decorator(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
        # -- Patch the docstring of the decorated function to add chunking strategy and
        # -- chunking-related argument documentation. This only applies when `chunking_strategy`
        # -- is an explicit argument of the decorated function and "chunking_strategy" is not
        # -- already mentioned in the docstring.
        if func.__doc__ and (
            "chunking_strategy" in func.__code__.co_varnames
            and "chunking_strategy" not in func.__doc__
        ):
            func.__doc__ += (
                "\nchunking_strategy"
                + "\n\tStrategy used for chunking text into larger or smaller elements."
                + "\n\tDefaults to `None` with optional arg of 'basic' or 'by_title'."
                + "\n\tAdditional Parameters:"
                + "\n\t\tmultipage_sections"
                + "\n\t\t\tIf True, sections can span multiple pages. Defaults to True."
                + "\n\t\tcombine_text_under_n_chars"
                + "\n\t\t\tCombines elements (for example a series of titles) until a section"
                + "\n\t\t\treaches a length of n characters. Only applies to 'by_title' strategy."
                + "\n\t\tnew_after_n_chars"
                + "\n\t\t\tCuts off chunks once they reach a length of n characters; a soft max."
                + "\n\t\tmax_characters"
                + "\n\t\t\tChunks elements text and text_as_html (if present) into chunks"
                + "\n\t\t\tof length n characters, a hard max."
            )

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> list[Element]:
            """The decorated function is replaced with this one."""

            def get_call_args_applying_defaults() -> dict[str, Any]:
                """Map both explicit and default arguments of decorated func call by param name."""
                sig = inspect.signature(func)
                call_args: dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
                for param in sig.parameters.values():
                    if param.name not in call_args and param.default is not param.empty:
                        call_args[param.name] = param.default
                return call_args

            # -- call the partitioning function to get the elements --
            elements = func(*args, **kwargs)

            # -- look for a chunking-strategy argument and run the indicated chunker when present --
            call_args = get_call_args_applying_defaults()

            if call_args.get("chunking_strategy") == "by_title":
                return chunk_by_title(
                    elements,
                    combine_text_under_n_chars=call_args.get("combine_text_under_n_chars", None),
                    max_characters=call_args.get("max_characters", CHUNK_MAX_CHARS_DEFAULT),
                    multipage_sections=call_args.get(
                        "multipage_sections", CHUNK_MULTI_PAGE_DEFAULT
                    ),
                    new_after_n_chars=call_args.get("new_after_n_chars", None),
                    overlap=call_args.get("overlap", 0),
                    overlap_all=call_args.get("overlap_all", False),
                )

            if call_args.get("chunking_strategy") == "basic":
                return chunk_elements(
                    elements,
                    max_characters=call_args.get("max_characters", CHUNK_MAX_CHARS_DEFAULT),
                    new_after_n_chars=call_args.get("new_after_n_chars", None),
                    overlap=call_args.get("overlap", 0),
                    overlap_all=call_args.get("overlap_all", False),
                )

            return elements

        return wrapper

    return decorator
