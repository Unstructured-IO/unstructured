"""Handles dispatch of elements to a chunking-strategy by name.

Also provides the `@add_chunking_strategy` decorator which is the chief current user of "by-name"
chunking dispatch.
"""

from __future__ import annotations

import dataclasses as dc
import functools
import inspect
from typing import Any, Callable, Iterable, Optional, Protocol

from typing_extensions import ParamSpec

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element
from unstructured.utils import get_call_args_applying_defaults, lazyproperty

_P = ParamSpec("_P")


class Chunker(Protocol):
    """Abstract interface for chunking functions."""

    def __call__(
        self, elements: Iterable[Element], *, max_characters: Optional[int]
    ) -> list[Element]:
        """A chunking function must have this signature.

        In particular it must minimally have an `elements` parameter and all chunkers will have a
        `max_characters` parameter (doesn't need to follow `elements` directly). All others can
        vary by chunker.
        """
        ...


def add_chunking_strategy(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
    """Decorator for chunking text.

    Chunks the element sequence produced by the partitioner it decorates when a `chunking_strategy`
    argument is present in the partitioner call and it names an available chunking strategy.
    """
    # -- Patch the docstring of the decorated function to add chunking strategy and
    # -- chunking-related argument documentation. This only applies when `chunking_strategy`
    # -- is an explicit argument of the decorated function and "chunking_strategy" is not
    # -- already mentioned in the docstring.
    if func.__doc__ and (
        "chunking_strategy" in func.__code__.co_varnames and "chunking_strategy" not in func.__doc__
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

        # -- call the partitioning function to get the elements --
        elements = func(*args, **kwargs)

        # -- look for a chunking-strategy argument --
        call_args = get_call_args_applying_defaults(func, *args, **kwargs)
        chunking_strategy = call_args.pop("chunking_strategy", None)

        # -- no chunking-strategy means no chunking --
        if chunking_strategy is None:
            return elements

        # -- otherwise, chunk away :) --
        return chunk(elements, chunking_strategy, **call_args)

    return wrapper


def chunk(elements: Iterable[Element], chunking_strategy: str, **kwargs: Any) -> list[Element]:
    """Dispatch chunking of `elements` to the chunking function for `chunking_strategy`."""
    chunker_spec = _chunker_registry.get(chunking_strategy)

    if chunker_spec is None:
        raise ValueError(f"unrecognized chunking strategy {repr(chunking_strategy)}")

    # -- `kwargs` will in general be an omnibus dict of all keyword arguments to the partitioner;
    # -- pick out and use only those supported by this chunker.
    chunking_kwargs = {k: v for k, v in kwargs.items() if k in chunker_spec.kw_arg_names}

    return chunker_spec.chunker(elements, **chunking_kwargs)


def register_chunking_strategy(name: str, chunker: Chunker) -> None:
    """Make chunker available by using `name` as `chunking_strategy` arg in partitioner call."""
    _chunker_registry[name] = _ChunkerSpec(chunker)


@dc.dataclass(frozen=True)
class _ChunkerSpec:
    """A registry entry for a chunker."""

    chunker: Chunker
    """The "chunk_by_{x}() function that implements this chunking strategy."""

    @lazyproperty
    def kw_arg_names(self) -> tuple[str, ...]:
        """Keyword arguments supported by this chunker.

        These are all arguments other than the required `elements: list[Element]` first parameter.
        """
        sig = inspect.signature(self.chunker)
        return tuple(key for key in sig.parameters if key != "elements")


_chunker_registry: dict[str, _ChunkerSpec] = {
    "basic": _ChunkerSpec(chunk_elements),
    "by_title": _ChunkerSpec(chunk_by_title),
}
