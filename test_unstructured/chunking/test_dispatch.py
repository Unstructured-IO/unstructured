# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.dispatch` module."""

from __future__ import annotations

from typing import Any

from unstructured.chunking import add_chunking_strategy
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


# -- MODULE-LEVEL FIXTURES -----------------------------------------------------------------------


def partition_this(**kwargs: Any) -> list[Element]:
    """A fake partitioner."""
    return [Text("Lorem ipsum."), Text("Sit amet.")]
