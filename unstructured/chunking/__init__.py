"""Chunking module initializer.

Provides the the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Dict, List

from typing_extensions import ParamSpec

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element

_P = ParamSpec("_P")


def add_chunking_strategy() -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """Decorator for chunking text.

    Chunks the element sequence produced by the partitioner it decorates when a `chunking_strategy`
    argument is present in the partitioner call and it names an available chunking strategy.
    """

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        if func.__doc__ and (
            "chunking_strategy" in func.__code__.co_varnames
            and "chunking_strategy" not in func.__doc__
        ):
            func.__doc__ += (
                "\nchunking_strategy"
                + "\n\tStrategy used for chunking text into larger or smaller elements."
                + "\n\tDefaults to `None` with optional arg of 'by_title'."
                + "\n\tAdditional Parameters:"
                + "\n\t\tmultipage_sections"
                + "\n\t\t\tIf True, sections can span multiple pages. Defaults to True."
                + "\n\t\tcombine_text_under_n_chars"
                + "\n\t\t\tCombines elements (for example a series of titles) until a section"
                + "\n\t\t\treaches a length of n characters."
                + "\n\t\tnew_after_n_chars"
                + "\n\t\t\tCuts off new sections once they reach a length of n characters"
                + "\n\t\t\ta soft max."
                + "\n\t\tmax_characters"
                + "\n\t\t\tChunks elements text and text_as_html (if present) into chunks"
                + "\n\t\t\tof length n characters, a hard max."
            )

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params: Dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default
            if params.get("chunking_strategy") == "by_title":
                elements = chunk_by_title(
                    elements,
                    multipage_sections=params.get("multipage_sections", True),
                    combine_text_under_n_chars=params.get("combine_text_under_n_chars", 500),
                    new_after_n_chars=params.get("new_after_n_chars", 500),
                    max_characters=params.get("max_characters", 500),
                )
            return elements

        return wrapper

    return decorator
