"""Public chunking API regressions for timestamp provenance across boundaries."""

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, Image, NarrativeText, Table, Title


@pytest.fixture(params=[chunk_elements, chunk_by_title], ids=["basic", "by_title"])
def chunk(request):
    """Keep forced boundaries visible in both public chunking strategies."""
    function = request.param

    def call(elements, **kwargs):
        if function is chunk_by_title:
            kwargs.setdefault("combine_text_under_n_chars", 0)
        return function(elements, **kwargs)

    return call


@pytest.fixture(params=[False, True], ids=["without_originals", "with_originals"])
def originals(request):
    return request.param


def segment(text, start=None, end=None, **metadata):
    """Build a source segment without inferring missing timestamps."""
    return NarrativeText(
        text,
        metadata=ElementMetadata(
            segment_start_seconds=start,
            segment_end_seconds=end,
            **metadata,
        ),
    )


def interval(element):
    return (element.metadata.segment_start_seconds, element.metadata.segment_end_seconds)


@pytest.mark.parametrize("boundary", ["hard", "soft"])
def test_overlap_interval_follows_text_across_forced_boundary(chunk, originals, boundary):
    first = segment("first source ends TAIL", 0.0, 10.0, filename="first.wav", languages=["en"])
    second = segment("second source has data", 60.0, 70.0, filename="second.wav", languages=["fr"])
    options = (
        {"max_characters": 32}
        if boundary == "hard"
        else {
            "max_characters": 100,
            "new_after_n_chars": 0,
        }
    )

    chunks = chunk(
        [first, second],
        overlap=4,
        overlap_all=True,
        include_orig_elements=originals,
        **options,
    )

    assert [item.text for item in chunks] == [first.text, "TAIL\n\n" + second.text]
    assert [interval(item) for item in chunks] == [(0.0, 10.0), (0.0, 70.0)]
    assert chunks[1].metadata.filename == "second.wav"
    assert chunks[1].metadata.languages == ["fr"]
    assert chunks[1].metadata.orig_elements == ([second] if originals else None)
    assert interval(second) == (60.0, 70.0)


def test_overlap_does_not_accumulate_expired_source_intervals(chunk, originals):
    elements = [
        segment("first source ends TAIL", 0.0, 10.0),
        segment("second source has data", 60.0, 70.0),
        segment("third source has words", 120.0, 130.0),
    ]

    chunks = chunk(
        elements,
        max_characters=100,
        new_after_n_chars=0,
        overlap=4,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == [
        elements[0].text,
        "TAIL\n\n" + elements[1].text,
        "data\n\n" + elements[2].text,
    ]
    assert [interval(item) for item in chunks] == [
        (0.0, 10.0),
        (0.0, 70.0),
        (60.0, 130.0),
    ]


def test_overlap_retains_old_prefix_provenance_while_its_text_remains(chunk, originals):
    elements = [
        segment("first source ends TAIL", 0.0, 10.0),
        segment("X", 60.0, 70.0),
        segment("third source", 120.0, 130.0),
    ]

    chunks = chunk(
        elements,
        max_characters=100,
        new_after_n_chars=0,
        overlap=6,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert len(chunks) == 3
    assert chunks[2].text == "AIL\n\nX\n\nthird source"
    assert interval(chunks[2]) == (0.0, 130.0)


@pytest.mark.parametrize(("overlap", "overlap_all"), [(4, False), (0, True)])
def test_no_overlap_does_not_broaden_the_next_interval(chunk, originals, overlap, overlap_all):
    elements = [segment("first TAIL", 0.0, 10.0), segment("second text", 60.0, 70.0)]

    chunks = chunk(
        elements,
        max_characters=100,
        new_after_n_chars=0,
        overlap=overlap,
        overlap_all=overlap_all,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == [item.text for item in elements]
    assert [interval(item) for item in chunks] == [(0.0, 10.0), (60.0, 70.0)]


@pytest.mark.parametrize("bounds", [(0.0, 0.0), (0.0, None), (None, 10.0), (None, None)])
def test_overlap_preserves_zero_and_partial_bounds_without_inference(chunk, originals, bounds):
    chunks = chunk(
        [segment("first TAIL", *bounds), segment("untimed second")],
        max_characters=100,
        new_after_n_chars=0,
        overlap=4,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert len(chunks) == 2
    assert chunks[1].text == "TAIL\n\nuntimed second"
    assert interval(chunks[1]) == bounds


def test_metadata_only_flush_carries_only_timestamps_into_oversized_text(chunk, originals):
    images = [
        Image(
            "",
            metadata=ElementMetadata(
                segment_start_seconds=0.0,
                segment_end_seconds=5.0,
                filename="frame.png",
                languages=["de"],
            ),
        ),
        Image(
            "",
            metadata=ElementMetadata(
                segment_start_seconds=3.0,
                segment_end_seconds=10.0,
                filename="other-frame.png",
                languages=["es"],
            ),
        ),
    ]
    text = segment("long audio segment " * 8, 60.0, 70.0, filename="speech.wav", languages=["en"])
    tail = segment("later segment", 120.0, 130.0, filename="later.wav", languages=["it"])

    chunks = chunk(
        [*images, text, tail],
        max_characters=24,
        overlap=0,
        include_orig_elements=originals,
    )

    assert len(chunks) > 2
    assert chunks[-1].text == tail.text
    assert all(interval(item) == (0.0, 70.0) for item in chunks[:-1])
    assert interval(chunks[-1]) == (120.0, 130.0)
    assert all(item.metadata.filename == "speech.wav" for item in chunks[:-1])
    assert all(item.metadata.languages == ["en"] for item in chunks[:-1])
    assert all(
        item.metadata.orig_elements == ([text] if originals else None) for item in chunks[:-1]
    )
    assert [interval(item) for item in images] == [(0.0, 5.0), (3.0, 10.0)]
    assert interval(text) == (60.0, 70.0)


def test_metadata_only_run_without_following_text_emits_no_synthetic_chunk(chunk, originals):
    images = [
        Image("", metadata=ElementMetadata(segment_start_seconds=0.0, segment_end_seconds=10.0))
    ]

    assert chunk(images, max_characters=24, include_orig_elements=originals) == []


def test_table_isolation_drops_overlap_text_and_its_timestamps(chunk, originals):
    elements = [
        segment("before TAIL", 0.0, 10.0),
        Table(
            "table cells",
            metadata=ElementMetadata(segment_start_seconds=60.0, segment_end_seconds=70.0),
        ),
        segment("after table", 120.0, 130.0),
    ]

    chunks = chunk(
        elements,
        max_characters=100,
        new_after_n_chars=0,
        overlap=4,
        overlap_all=True,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == [item.text for item in elements]
    assert [interval(item) for item in chunks] == [(0.0, 10.0), (60.0, 70.0), (120.0, 130.0)]


def test_by_title_carries_range_across_successive_textless_page_flushes(originals):
    images = [
        Image(
            "",
            metadata=ElementMetadata(
                segment_start_seconds=0.0, segment_end_seconds=10.0, page_number=1
            ),
        ),
        Image(
            "",
            metadata=ElementMetadata(
                segment_start_seconds=20.0, segment_end_seconds=30.0, page_number=2
            ),
        ),
    ]
    text = segment("long audio segment " * 8, 60.0, 70.0, page_number=3)

    chunks = chunk_by_title(
        [*images, text],
        max_characters=24,
        combine_text_under_n_chars=0,
        multipage_sections=False,
        include_orig_elements=originals,
    )

    assert len(chunks) > 1
    assert all(interval(item) == (0.0, 70.0) for item in chunks)
    assert all(item.metadata.page_number == 3 for item in chunks)


def test_by_title_recombination_keeps_existing_element_metadata(originals):
    image = Image(
        "",
        metadata=ElementMetadata(
            segment_start_seconds=0.0, segment_end_seconds=10.0, filename="frame.png"
        ),
    )
    title = Title(
        "First",
        metadata=ElementMetadata(
            segment_start_seconds=60.0, segment_end_seconds=70.0, filename="text.wav"
        ),
    )
    second = Title(
        "Second",
        metadata=ElementMetadata(
            segment_start_seconds=120.0, segment_end_seconds=130.0, filename="later.wav"
        ),
    )

    chunks = chunk_by_title(
        [image, title, second],
        max_characters=100,
        combine_text_under_n_chars=100,
        include_orig_elements=originals,
    )

    assert len(chunks) == 1
    assert chunks[0].text == "First\n\nSecond"
    assert interval(chunks[0]) == (0.0, 130.0)
    assert chunks[0].metadata.filename == "frame.png"
    assert chunks[0].metadata.orig_elements == ([image, title, second] if originals else None)


@pytest.mark.parametrize("skip_table_chunking", [False, True])
def test_metadata_only_bounds_do_not_mutate_a_following_table(
    chunk, originals, skip_table_chunking
):
    image = Image("", metadata=ElementMetadata(segment_start_seconds=0.0, segment_end_seconds=10.0))
    table = Table(
        "table cells",
        metadata=ElementMetadata(segment_start_seconds=60.0, segment_end_seconds=70.0),
    )
    tail = segment("later text", 120.0, 130.0)

    chunks = chunk(
        [image, table, tail],
        max_characters=100,
        skip_table_chunking=skip_table_chunking,
        include_orig_elements=originals,
    )

    assert [item.text for item in chunks] == [table.text, tail.text]
    assert [interval(item) for item in chunks] == [(0.0, 70.0), (120.0, 130.0)]
    assert interval(table) == (60.0, 70.0)
    assert interval(image) == (0.0, 10.0)


@pytest.mark.parametrize("skip_table_chunking", [False, True])
def test_empty_table_bounds_are_carried_only_when_it_emits_no_chunk(
    chunk, originals, skip_table_chunking
):
    table = Table("", metadata=ElementMetadata(segment_start_seconds=0.0, segment_end_seconds=10.0))
    tail = segment("following text", 60.0, 70.0)

    chunks = chunk(
        [table, tail],
        max_characters=100,
        skip_table_chunking=skip_table_chunking,
        include_orig_elements=originals,
    )

    if skip_table_chunking:
        assert chunks[0] is table
        assert [interval(item) for item in chunks] == [(0.0, 10.0), (60.0, 70.0)]
    else:
        assert len(chunks) == 1
        assert interval(chunks[0]) == (0.0, 70.0)
    assert chunks[-1].text == tail.text
    assert interval(table) == (0.0, 10.0)
    assert interval(tail) == (60.0, 70.0)
