"""Public API interactions between overlap-only suppression and source time ranges."""

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import CodeSnippet, ElementMetadata, Text


@pytest.fixture(params=[chunk_elements, chunk_by_title], ids=["basic", "by_title"])
def chunk(request):
    function = request.param

    def call(elements, **kwargs):
        if function is chunk_by_title:
            kwargs.setdefault("combine_text_under_n_chars", 0)
        return function(elements, **kwargs)

    return call


@pytest.fixture(params=[False, True], ids=["without_originals", "with_originals"])
def originals(request):
    return request.param


def timed(kind, text, start, end):
    return kind(
        text, metadata=ElementMetadata(segment_start_seconds=start, segment_end_seconds=end)
    )


def bounds(element):
    return (element.metadata.segment_start_seconds, element.metadata.segment_end_seconds)


def test_retained_overlap_splits_keep_ranges_without_accumulating_older_sources(chunk, originals):
    elements = [
        timed(Text, "Lorem ipsum dolor sit amet, consectetur.", 0.0, 10.0),
        timed(Text, "In rhoncus ipsum sed lectus porta volutpat, ut aliquet magna.", 60.0, 70.0),
        timed(Text, "Final transcript segment.", 120.0, 130.0),
    ]

    chunks = chunk(
        elements,
        max_characters=50,
        overlap=10,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == [
        "Lorem ipsum dolor sit amet, consectetur.",
        "nsectetur.\n\nIn rhoncus ipsum sed lectus porta",
        "tus porta volutpat, ut aliquet magna.",
        "uet magna.\n\nFinal transcript segment.",
    ]
    assert [bounds(item) for item in chunks] == [
        (0.0, 10.0),
        (0.0, 70.0),
        (0.0, 70.0),
        (60.0, 130.0),
    ]
    assert not chunks[1].metadata.is_continuation
    assert chunks[2].metadata.is_continuation is True
    assert not chunks[3].metadata.is_continuation
    assert [bounds(item) for item in elements] == [(0.0, 10.0), (60.0, 70.0), (120.0, 130.0)]


def test_dropped_prefix_has_no_time_range_even_when_new_text_begins_with_same_characters(
    chunk, originals
):
    elements = [
        timed(Text, "abcdefghij", 0.0, 10.0),
        timed(Text, "abcdefghijABCDEFGHIJKLMNOP", 60.0, 70.0),
    ]

    chunks = chunk(
        elements,
        max_characters=11,
        overlap=10,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert chunks[0].text == "abcdefghij"
    assert chunks[1].text == "abcdefghijA"
    assert len(chunks) > 2
    assert all(len(item.text) <= 11 for item in chunks)
    assert chunks[-1].text.endswith("P")
    assert bounds(chunks[0]) == (0.0, 10.0)
    assert all(bounds(item) == (60.0, 70.0) for item in chunks[1:])
    assert not chunks[1].metadata.is_continuation
    assert bounds(elements[1]) == (60.0, 70.0)


def test_leading_code_whitespace_drops_prefix_range_and_preserves_first_fragment_metadata(
    chunk, originals
):
    elements = [
        timed(Text, "abcdefghij", 0.0, 10.0),
        timed(CodeSnippet, " " * 50 + "z", 60.0, 70.0),
    ]

    chunks = chunk(
        elements,
        max_characters=50,
        overlap=10,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == ["abcdefghij", "z"]
    assert [bounds(item) for item in chunks] == [(0.0, 10.0), (60.0, 70.0)]
    assert not chunks[1].metadata.is_continuation
    assert chunks[1].metadata.orig_elements == ([elements[1]] if originals else None)


def test_genuine_short_fragment_keeps_its_range_without_synthetic_prefix(chunk, originals):
    element = timed(CodeSnippet, "abcdefghij" + " " * 20 + "z", 60.0, 70.0)

    chunks = chunk(
        [element],
        max_characters=11,
        overlap=10,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == ["abcdefghij", "bcdefghij z"]
    assert [bounds(item) for item in chunks] == [(60.0, 70.0), (60.0, 70.0)]
    assert not chunks[0].metadata.is_continuation
    assert chunks[1].metadata.is_continuation is True


@pytest.mark.parametrize("space_count", [50, 51])
def test_pending_range_tracks_actual_emission_of_whitespace_code(chunk, originals, space_count):
    first = timed(Text, "abcdefghij", 0.0, 10.0)
    whitespace = CodeSnippet(
        " " * space_count,
        metadata=ElementMetadata(
            segment_start_seconds=60.0,
            segment_end_seconds=70.0,
            filename="whitespace.source",
            languages=["de"],
        ),
    )
    tail = Text(
        "after whitespace",
        metadata=ElementMetadata(
            segment_start_seconds=120.0,
            segment_end_seconds=130.0,
            filename="tail.source",
            languages=["fr"],
        ),
    )

    chunks = chunk(
        [first, whitespace, tail],
        max_characters=50,
        overlap=10,
        overlap_all=True,
        include_orig_elements=originals,
    )

    if space_count == 50:
        assert [item.text for item in chunks] == ["abcdefghij", " " * 50, "after whitespace"]
        assert [bounds(item) for item in chunks] == [(0.0, 10.0), (60.0, 70.0), (120.0, 130.0)]
        assert not chunks[1].metadata.is_continuation
    else:
        assert [item.text for item in chunks] == ["abcdefghij", "after whitespace"]
        assert [bounds(item) for item in chunks] == [(0.0, 10.0), (60.0, 130.0)]
    assert not chunks[-1].metadata.is_continuation
    assert chunks[-1].metadata.filename == "tail.source"
    assert chunks[-1].metadata.languages == ["fr"]
    assert chunks[-1].metadata.orig_elements == ([tail] if originals else None)
    assert bounds(whitespace) == (60.0, 70.0)
    assert bounds(tail) == (120.0, 130.0)
