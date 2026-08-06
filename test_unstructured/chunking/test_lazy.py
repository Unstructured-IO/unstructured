"""Test suite for the lazy chunking entry points.

`iter_chunk_elements()` and `iter_chunks_by_title()` expose the generator pipeline that
`chunk_elements()` and `chunk_by_title()` have always driven internally. What matters is that
they are (a) equivalent to their list-returning counterparts and (b) actually lazy, since a
caller only reaches for them to avoid materializing the document.
"""

from __future__ import annotations

import gc
import inspect
import weakref
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

# -- the two (list-form, generator-form) pairs under test --
_PAIRS = [
    pytest.param(chunk_elements, iter_chunk_elements, id="basic"),
    pytest.param(chunk_by_title, iter_chunks_by_title, id="by_title"),
]


# -- the chunking window every equivalence test uses; the document below is sized against it --
_MAX_CHARACTERS = 250

_TABLE_ROWS = tuple((f"Region {i:02d}", f"{i * 1000}") for i in range(20))

# -- `<thead>`/`<th>` mark the leading row as a header, which is what `repeat_table_headers`
# -- carries onto continuation chunks --
_TABLE_HTML = (
    "<table><thead><tr><th>Region</th><th>Revenue</th></tr></thead><tbody>"
    + "".join(f"<tr><td>{name}</td><td>{revenue}</td></tr>" for name, revenue in _TABLE_ROWS)
    + "</tbody></table>"
)

_TABLE_TEXT = "Region Revenue " + " ".join(f"{name} {revenue}" for name, revenue in _TABLE_ROWS)

_SMALL_TABLE_HTML = (
    "<table><tr><td>Qty</td><td>Price</td></tr><tr><td>2</td><td>10</td></tr></table>"
)


def _document() -> list[Element]:
    """A document shaped so that every option under test changes the chunks it produces.

    An option that made no difference here would leave the equivalence tests toothless -- a
    dropped option would produce identical output either way -- so the sizes are deliberate:

    - Sections are short enough to combine and to be cut early by a soft maximum.
    - One table's *text* exceeds the window, so it divides into `TableChunk`s with a repeated
      header row.
    - A second table is small and surrounded by short text, so isolating tables matters.
    - One narrative element exceeds the window on its own, so it is text-split and overlap
      applies.
    - The final section spans a page boundary in three pieces that do not all fit in one
      window, so breaking on that boundary moves where the split lands.

    `element_id` is pinned rather than left to default. Ids are random UUIDs, and
    `include_orig_elements=True` carries them into the chunk's encoded `orig_elements`, so
    two independently-built copies of the same document would not compare equal.
    """
    return [
        # -- a section short enough that it combines with the next one by default --
        Title("Introduction", element_id="e1", metadata=ElementMetadata(page_number=1)),
        NarrativeText(
            "Lorem ipsum dolor sit amet. " * 2,
            element_id="e2",
            metadata=ElementMetadata(page_number=1),
        ),
        Title("Quarterly Data", element_id="e3", metadata=ElementMetadata(page_number=1)),
        NarrativeText(
            "Consectetur adipiscing elit. " * 2,
            element_id="e4",
            metadata=ElementMetadata(page_number=1),
        ),
        # -- small enough to share a pre-chunk with the text around it, which is the only way
        # -- `isolate_table` is observable; an oversized table is isolated regardless --
        Table(
            "Qty Price 2 10",
            element_id="e5",
            metadata=ElementMetadata(page_number=1, text_as_html=_SMALL_TABLE_HTML),
        ),
        Table(
            _TABLE_TEXT,
            element_id="e6",
            metadata=ElementMetadata(page_number=1, text_as_html=_TABLE_HTML),
        ),
        NarrativeText(
            "Tables above, prose below. " * 2,
            element_id="e7",
            metadata=ElementMetadata(page_number=1),
        ),
        Title("Results", element_id="e8", metadata=ElementMetadata(page_number=2)),
        # -- oversized on its own, so it is text-split --
        NarrativeText(
            "Sed do eiusmod tempor incididunt ut labore. " * 8,
            element_id="e9",
            metadata=ElementMetadata(page_number=2),
        ),
        NarrativeText(
            "Ut enim ad minim veniam, quis nostrud. " * 3,
            element_id="e10",
            metadata=ElementMetadata(page_number=2),
        ),
        # -- same section, next page: no title intervenes, so only `multipage_sections` splits
        # -- here, and the three pieces together overflow the window --
        NarrativeText(
            "Duis aute irure dolor in reprehenderit. " * 3,
            element_id="e11",
            metadata=ElementMetadata(page_number=3),
        ),
        NarrativeText(
            "Excepteur sint occaecat cupidatat non. " * 3,
            element_id="e12",
            metadata=ElementMetadata(page_number=3),
        ),
    ]


def _comparable(chunks: list[Element]) -> list[dict[str, Any]]:
    """Serialize chunks, neutralizing the two fields that are legitimately unstable.

    `element_id` is a fresh UUID per chunk and `metadata.table_id` a fresh UUID per divided
    table, so both differ between two runs of the *same* function; comparing them would
    assert nondeterminism rather than equivalence. `table_id` is replaced by a first-seen
    ordinal rather than dropped, so the grouping it encodes is still compared. Everything
    else, `metadata.orig_elements` included, must match.
    """
    dicts = elements_to_dicts(chunks)
    table_ids: dict[str, int] = {}
    for d in dicts:
        d.pop("element_id", None)
        metadata = d.get("metadata", {})
        if (table_id := metadata.get("table_id")) is not None:
            metadata["table_id"] = table_ids.setdefault(table_id, len(table_ids))
    return dicts


def _assert_equivalent(
    chunk_fn: Callable[..., list[Element]],
    iter_fn: Callable[..., Iterator[Element]],
    **kwargs: Any,
):
    """The generator form must produce the same chunks, in the same order, as the list form."""
    buffered = chunk_fn(_document(), **kwargs)
    streamed = list(iter_fn(iter(_document()), **kwargs))

    assert _comparable(streamed) == _comparable(buffered)


# -- option sets both strategies share. Each one chunks `_document()` differently from the
# -- defaults; `test_the_equivalence_option_sets_each_change_the_chunks` holds that line.
_SHARED_OPTION_SETS = [
    ("defaults", {}),
    ("no_orig_elements", {"include_orig_elements": False}),
    ("overlap_split_chunks_only", {"overlap": 10}),
    ("overlap_all", {"overlap": 10, "overlap_all": True}),
    ("table_shares_pre_chunk", {"isolate_table": False}),
    ("table_not_divided", {"skip_table_chunking": True}),
    ("no_repeated_headers", {"repeat_table_headers": False}),
]

_BASIC_OPTION_SETS = [
    *_SHARED_OPTION_SETS,
    ("soft_max", {"new_after_n_chars": 100}),
]

_BY_TITLE_OPTION_SETS = [
    *_SHARED_OPTION_SETS,
    # -- by-title combines undersized pre-chunks after the soft maximum has cut them, and by
    # -- default combines up to `max_characters`, which puts them right back together. Suppress
    # -- combining to see the soft maximum at all.
    ("soft_max", {"new_after_n_chars": 100, "combine_text_under_n_chars": 0}),
    # -- and these two options are by-title's alone --
    ("no_combining", {"combine_text_under_n_chars": 0}),
    ("break_on_page_boundary", {"multipage_sections": False}),
]


def _option_set_params() -> list[Any]:
    """(chunk_fn, iter_fn, options) triples, one per strategy per option set."""
    return [
        pytest.param(chunk_fn, iter_fn, options, id=f"{pair_id}-{set_id}")
        for pair_id, chunk_fn, iter_fn, option_sets in (
            ("basic", chunk_elements, iter_chunk_elements, _BASIC_OPTION_SETS),
            ("by_title", chunk_by_title, iter_chunks_by_title, _BY_TITLE_OPTION_SETS),
        )
        for set_id, options in option_sets
    ]


@pytest.mark.parametrize(("chunk_fn", "iter_fn", "options"), _option_set_params())
def test_lazy_chunking_matches_the_list_form(
    chunk_fn: Callable[..., list[Element]],
    iter_fn: Callable[..., Iterator[Element]],
    options: dict[str, Any],
):
    """Each option must be plumbed through the generator form exactly as through the list form.

    Signature parity cannot show this: each wrapper builds its own
    `_...ChunkingOptions.new()` call, so an option dropped or miswired in only one of them
    still passes with matching signatures. That only shows up in the chunks.
    """
    _assert_equivalent(chunk_fn, iter_fn, max_characters=_MAX_CHARACTERS, **options)


@pytest.mark.parametrize(("chunk_fn", "iter_fn", "options"), _option_set_params())
def test_the_equivalence_option_sets_each_change_the_chunks(
    chunk_fn: Callable[..., list[Element]],
    iter_fn: Callable[..., Iterator[Element]],
    options: dict[str, Any],
):
    """Guards the guard above: every option set must actually chunk `_document()` differently.

    A set that produced the default chunks would prove nothing about plumbing, since a
    dropped option produces exactly that same output.
    """
    if not options:
        pytest.skip("the default set is the baseline the others are compared against")

    default = chunk_fn(_document(), max_characters=_MAX_CHARACTERS)
    with_options = chunk_fn(_document(), max_characters=_MAX_CHARACTERS, **options)

    assert _comparable(with_options) != _comparable(default), (
        f"{options} chunks `_document()` exactly as the defaults do, so the equivalence test"
        f" would not notice the option being dropped"
    )


@pytest.mark.parametrize(("chunk_fn", "iter_fn"), _PAIRS)
def test_lazy_chunking_matches_the_list_form_for_token_based_options(
    chunk_fn: Callable[..., list[Element]], iter_fn: Callable[..., Iterator[Element]]
):
    """The token-based window and its soft maximum, which replace the character-based pair."""
    pytest.importorskip("tiktoken")

    _assert_equivalent(
        chunk_fn,
        iter_fn,
        max_tokens=64,
        new_after_n_tokens=32,
        tokenizer="cl100k_base",
    )


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

    # -- a chunk closes as soon as the element that overflows it arrives, so producing one
    # -- costs a handful of elements: the pre-chunk's own, plus the lookahead that closes it --
    next(chunks)
    first = consumed
    assert 0 < first <= 8, f"drained {first} of 400 elements to yield one chunk"

    # -- and the cost per chunk stays flat; a growing internal buffer would show up here --
    next(chunks)
    assert consumed - first <= 8, (
        f"second chunk cost {consumed - first} elements against the first chunk's {first}"
    )


@pytest.mark.parametrize(
    ("iter_fn", "pre_chunks_held"),
    [
        (iter_chunk_elements, 1),
        # -- by-title reads one pre-chunk ahead to combine undersized ones --
        (iter_chunks_by_title, 2),
    ],
)
def test_lazy_chunking_releases_each_pre_chunk_before_forming_the_next(
    iter_fn: Callable[..., Iterator[Element]], pre_chunks_held: int
):
    """Elements held at once must stay flat, not creep up as the document is consumed.

    Yielding chunks lazily is not enough on its own: the emitted pre-chunk stays bound to the
    generator's loop variable while the next one fills, so without an explicit release a
    streaming caller holds one pre-chunk more than the strategy needs.
    """
    elements_per_pre_chunk = 4  # -- four ~70-character elements fill a 250-character window --
    refs: list[weakref.ReferenceType[Element]] = []
    live: list[int] = []

    def source() -> Iterator[Element]:
        for i in range(200):
            element = NarrativeText(f"element {i:03d} " * 5)
            refs.append(weakref.ref(element))
            yield element
            gc.collect()
            live.append(sum(1 for ref in refs if ref() is not None))

    chunks = iter_fn(source(), max_characters=250, include_orig_elements=False)
    for _ in range(6):
        next(chunks)

    assert max(live) <= elements_per_pre_chunk * pre_chunks_held, (
        f"held {max(live)} source elements at once, more than the"
        f" {pre_chunks_held} pre-chunk(s) this strategy needs"
    )


@pytest.mark.parametrize("iter_fn", [iter_chunk_elements, iter_chunks_by_title])
def test_lazy_chunking_validates_its_options_eagerly(iter_fn: Callable[..., Iterator[Element]]):
    """A bad option must raise at the call, not at first advance.

    A plain generator function would defer the whole body, so the `ValueError` would surface
    somewhere else entirely -- or, for a document that yields no chunks, not at all. Matches
    when `chunk_elements()` and `chunk_by_title()` raise.
    """
    with pytest.raises(ValueError):
        iter_fn([], max_characters=500, new_after_n_chars=-3)


@pytest.mark.parametrize(("chunk_fn", "iter_fn"), _PAIRS)
def test_lazy_chunking_validates_its_tokenizer_eagerly(
    chunk_fn: Callable[..., list[Element]], iter_fn: Callable[..., Iterator[Element]]
):
    """An unknown tokenizer must also raise at the call, in both forms.

    The encoder is resolved on first use, which for the list form happens during the call but
    for the generator form would happen on first advance -- exactly the deferred error the
    eager-validation contract promises not to produce.
    """
    pytest.importorskip("tiktoken")
    kwargs = {"max_tokens": 64, "tokenizer": "not-a-real-tokenizer"}

    with pytest.raises(ValueError, match="not-a-real-tokenizer"):
        chunk_fn(_document(), **kwargs)

    with pytest.raises(ValueError, match="not-a-real-tokenizer"):
        iter_fn(iter(_document()), **kwargs)


@pytest.mark.parametrize(("chunk_fn", "iter_fn"), _PAIRS)
def test_lazy_chunking_accepts_the_same_options(
    chunk_fn: Callable[..., list[Element]], iter_fn: Callable[..., Iterator[Element]]
):
    """Guards against the two signatures drifting apart as options are added.

    Compares the full parameter mapping, not just the names, so a default value or a
    keyword-only marker that changes on one side alone is caught too.
    """
    assert inspect.signature(iter_fn).parameters == inspect.signature(chunk_fn).parameters
