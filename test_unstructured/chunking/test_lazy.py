"""Test suite for the lazy chunking entry points.

`iter_chunk_elements()` and `iter_chunks_by_title()` expose the generator pipeline that
`chunk_elements()` and `chunk_by_title()` have always driven internally. What matters is that
they are (a) equivalent to their list-returning counterparts and (b) actually lazy, since a
caller only reaches for them to avoid materializing the document.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator

import pytest

from unstructured.chunking.basic import chunk_elements, iter_chunk_elements
from unstructured.chunking.title import chunk_by_title, iter_chunks_by_title
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    NarrativeText,
    Table,
    Title,
)
from unstructured.staging.base import elements_to_dicts


def _document() -> list[Element]:
    """A few sections, a couple of pages and a table, to exercise both strategies.

    `element_id` is pinned rather than left to default. Ids are random UUIDs, and
    `include_orig_elements=True` carries them into the chunk's encoded `orig_elements`, so
    two independently-built copies of the same document would not compare equal.
    """
    return [
        Title("Introduction", element_id="e1", metadata=ElementMetadata(page_number=1)),
        NarrativeText(
            "Lorem ipsum dolor sit amet, " * 12,
            element_id="e2",
            metadata=ElementMetadata(page_number=1),
        ),
        NarrativeText(
            "Consectetur adipiscing elit. " * 12,
            element_id="e3",
            metadata=ElementMetadata(page_number=1),
        ),
        Title("Results", element_id="e4", metadata=ElementMetadata(page_number=2)),
        Table(
            "a b c",
            element_id="e5",
            metadata=ElementMetadata(page_number=2, text_as_html="<table/>"),
        ),
        NarrativeText(
            "Sed do eiusmod tempor incididunt. " * 12,
            element_id="e6",
            metadata=ElementMetadata(page_number=2),
        ),
        Title("Conclusion", element_id="e7", metadata=ElementMetadata(page_number=3)),
        NarrativeText(
            "Ut enim ad minim veniam. " * 12,
            element_id="e8",
            metadata=ElementMetadata(page_number=3),
        ),
    ]


def _comparable(chunks: list[Element]) -> list[dict[str, Any]]:
    """Serialize chunks, dropping the one field that is legitimately unstable.

    `element_id` is a fresh UUID per chunk, so it differs between two runs of the *same*
    function; comparing it would assert nondeterminism rather than equivalence. Everything
    else, `metadata.orig_elements` included, must match.
    """
    dicts = elements_to_dicts(chunks)
    for d in dicts:
        d.pop("element_id", None)
    return dicts


@pytest.mark.parametrize(
    ("chunk_fn", "iter_fn"),
    [(chunk_elements, iter_chunk_elements), (chunk_by_title, iter_chunks_by_title)],
)
@pytest.mark.parametrize("include_orig_elements", [True, False])
def test_lazy_chunking_matches_the_list_form(
    chunk_fn: Callable[..., list[Element]],
    iter_fn: Callable[..., Iterator[Element]],
    include_orig_elements: bool,
):
    kwargs = {"max_characters": 250, "include_orig_elements": include_orig_elements}

    buffered = chunk_fn(_document(), **kwargs)
    streamed = list(iter_fn(iter(_document()), **kwargs))

    assert _comparable(streamed) == _comparable(buffered)


@pytest.mark.parametrize("iter_fn", [iter_chunk_elements, iter_chunks_by_title])
def test_lazy_chunking_does_not_drain_its_source_to_yield_the_first_chunk(
    iter_fn: Callable[..., Iterator[Element]],
):
    """The point of the generator form: peak memory tracks a pre-chunk, not the document."""
    consumed = 0

    def source() -> Iterator[Element]:
        nonlocal consumed
        # -- each title opens a new section, so chunks close early and often --
        for i in range(200):
            consumed += 1
            yield Title(f"Section {i}")
            consumed += 1
            yield NarrativeText(f"Body of section {i}. " * 8)

    chunks = iter_fn(source(), max_characters=250)
    assert consumed == 0, "options-only call should not touch the source"

    next(chunks)
    assert 0 < consumed < 400, f"drained {consumed} of 400 elements to yield one chunk"


@pytest.mark.parametrize("iter_fn", [iter_chunk_elements, iter_chunks_by_title])
def test_lazy_chunking_validates_its_options_eagerly(iter_fn: Callable[..., Iterator[Element]]):
    """A bad option must raise at the call, not at first advance.

    A plain generator function would defer the whole body, so the `ValueError` would surface
    somewhere else entirely -- or, for a document that yields no chunks, not at all. Matches
    when `chunk_elements()` and `chunk_by_title()` raise.
    """
    with pytest.raises(ValueError):
        iter_fn([], max_characters=500, new_after_n_chars=-3)


@pytest.mark.parametrize(
    ("chunk_fn", "iter_fn"),
    [(chunk_elements, iter_chunk_elements), (chunk_by_title, iter_chunks_by_title)],
)
def test_lazy_chunking_accepts_the_same_options(
    chunk_fn: Callable[..., list[Element]], iter_fn: Callable[..., Iterator[Element]]
):
    """Guards against the two signatures drifting apart as options are added."""
    assert inspect.signature(iter_fn).parameters.keys() == (
        inspect.signature(chunk_fn).parameters.keys()
    )
