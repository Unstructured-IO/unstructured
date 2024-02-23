# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.dispatch` module."""

from __future__ import annotations

from typing import Any, Iterable, Optional

import pytest

from unstructured.chunking import add_chunking_strategy, register_chunking_strategy
from unstructured.chunking.dispatch import _ChunkerSpec, chunk
from unstructured.documents.elements import CompositeElement, Element, Text


class Describe_add_chunking_strategy:
    """Unit-test suite for `unstructured.chunking.add_chunking_strategy()` decorator."""

    def it_dispatches_the_partitioned_elements_to_the_indicated_chunker(self):
        decorated_partitioner = add_chunking_strategy(partition_this)

        chunks = decorated_partitioner(chunking_strategy="basic")

        assert chunks == [CompositeElement("Lorem ipsum.\n\nSit amet.")]

    def but_it_skips_dispatch_when_no_chunking_strategy_is_specified(self):
        decorated_partitioner = add_chunking_strategy(partition_this)

        elements = decorated_partitioner()

        assert elements == [Text("Lorem ipsum."), Text("Sit amet.")]


class Describe_chunk:
    """Unit-test suite for `unstructured.chunking.dispatch.chunk()` function."""

    def it_dispatches_to_the_chunker_registered_for_the_chunking_strategy(self):

        register_chunking_strategy("by_something_else", chunk_by_something_else)
        kwargs = {
            "max_characters": 750,
            # -- unused kwargs shouldn't cause a problem; in general `kwargs` will contain all
            # -- keyword arguments used in the partitioning call.
            "foo": "bar",
        }

        chunks = chunk([Text("Lorem"), Text("Ipsum")], "by_something_else", **kwargs)

        assert chunks == [
            CompositeElement("chunked 2 elements with `(max_characters=750, whizbang=None)`")
        ]

    def it_raises_when_the_requested_chunking_strategy_is_not_registered(self):
        with pytest.raises(
            ValueError,
            match="unrecognized chunking strategy 'foobar'",
        ):
            chunk(elements=[], chunking_strategy="foobar")


class Describe_ChunkerSpec:
    """Unit-test suite for `unstructured.chunking.dispatch._ChunkerSpec` objects."""

    def it_provides_access_to_the_chunking_function(self):
        spec = _ChunkerSpec(chunk_by_something_else)
        assert spec.chunker is chunk_by_something_else

    def it_knows_which_keyword_args_the_chunking_function_can_accept(self):
        spec = _ChunkerSpec(chunk_by_something_else)
        assert spec.kw_arg_names == ("max_characters", "whizbang")


# -- MODULE-LEVEL FIXTURES -----------------------------------------------------------------------


def chunk_by_something_else(
    elements: Iterable[Element],
    max_characters: Optional[int] = None,
    whizbang: Optional[float] = None,
) -> list[Element]:
    """A "fake" minimal chunker suitable for use in tests."""
    els = list(elements)
    return [
        CompositeElement(
            f"chunked {len(els)} elements with"
            f" `(max_characters={max_characters}, whizbang={whizbang})`"
        )
    ]


def partition_this(**kwargs: Any) -> list[Element]:
    """A fake partitioner."""
    return [Text("Lorem ipsum."), Text("Sit amet.")]
