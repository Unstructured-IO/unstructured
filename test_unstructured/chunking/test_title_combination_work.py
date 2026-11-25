"""Public title chunking work bounds and combination compatibility."""

import pytest

from unstructured.chunking import base, title
from unstructured.chunking.base import ChunkingOptions, PreChunk, PreChunkCombiner
from unstructured.chunking.title import chunk_by_title, iter_chunks_by_title
from unstructured.documents.elements import (
    CodeSnippet,
    ElementMetadata,
    Image,
    PageBreak,
    Table,
    TableChunk,
    Title,
)


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
@pytest.mark.parametrize("isolate_table", [False, True])
@pytest.mark.parametrize("count", [128, 256])
def test_combining_small_sections_does_linear_work(chunk, isolate_table, count, monkeypatch):
    elements = [Title(f"Section {index}") for index in range(count)]
    work = {"segments": 0, "combined_elements": 0, "table_checks": 0}
    original_segments = PreChunk._iter_text_segments
    original_combine = PreChunk.combine
    original_table_check = base._element_is_table_family

    def segments(self):
        for segment in original_segments(self):
            work["segments"] += 1
            yield segment

    def combine(self, other):
        work["combined_elements"] += len(self._elements) + len(other._elements)
        return original_combine(self, other)

    def table_check(element):
        work["table_checks"] += 1
        return original_table_check(element)

    monkeypatch.setattr(PreChunk, "_iter_text_segments", segments)
    monkeypatch.setattr(PreChunk, "combine", combine)
    monkeypatch.setattr(base, "_element_is_table_family", table_check)

    chunks = list(
        chunk(
            elements,
            max_characters=20 * count,
            combine_text_under_n_chars=20 * count,
            include_orig_elements=False,
            isolate_table=isolate_table,
        )
    )

    assert [c.text for c in chunks] == ["\n\n".join(e.text for e in elements)]
    assert chunks[0].metadata.orig_elements is None
    assert work["segments"] <= 6 * count
    assert work["combined_elements"] <= 4 * count
    assert work["table_checks"] <= 12 * count


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
def test_combination_retains_only_the_first_overlap_and_original_metadata(chunk):
    words = ["alpha", "beta", "gamma", "delta", "epsilon"]
    elements = [
        Title(word, metadata=ElementMetadata(filename="source.pdf", page_number=index + 1))
        for index, word in enumerate(words)
    ]

    chunks = list(chunk(elements, max_characters=20, overlap=3, overlap_all=True))

    assert [c.text for c in chunks] == ["alpha\n\nbeta\n\ngamma", "mma\n\ndelta\n\nepsilon"]
    assert [c.metadata.filename for c in chunks] == ["source.pdf", "source.pdf"]
    assert [c.metadata.page_number for c in chunks] == [1, 4]
    assert [c.metadata.orig_elements for c in chunks] == [elements[:3], elements[3:]]
    assert [e.metadata.page_number for e in elements] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
def test_empty_sections_and_code_keep_their_text_and_metadata(chunk):
    elements = [
        Title("  \n "),
        PageBreak(""),
        Title("  one  "),
        CodeSnippet("  x = 1\n  y = 2\n"),
        Title("two"),
        Image(""),
        Title(""),
    ]

    chunks = list(chunk(elements, max_characters=100))

    assert [c.text for c in chunks] == ["one\n\n  x = 1\n  y = 2\n\n\ntwo"]
    assert chunks[0].metadata.orig_elements == elements


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
def test_tables_still_isolate_sections_and_skip_keeps_the_original_table(chunk):
    table = Table("table text")
    elements = [Title("before"), table, Title("after"), TableChunk("tail table"), Title("last")]

    chunks = list(chunk(elements, max_characters=100))
    skipped = list(chunk(elements, max_characters=100, skip_table_chunking=True))

    assert [(c.category, c.text) for c in chunks] == [
        ("CompositeElement", "before"),
        ("Table", "table text"),
        ("CompositeElement", "after"),
        ("Table", "tail table"),
        ("CompositeElement", "last"),
    ]
    assert skipped[1] is table


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
@pytest.mark.parametrize(
    ("separator", "expected"),
    [("", ["abbccc"]), ("|", ["a|bb", "ccc"]), ("::", ["a::bb", "ccc"])],
)
def test_custom_text_separators_count_only_between_nonempty_sections(
    chunk, separator, expected, monkeypatch
):
    monkeypatch.setattr(ChunkingOptions, "text_separator", property(lambda self: separator))
    elements = [Title("a"), Title(""), Title("bb"), Title("  "), Title("ccc")]

    chunks = list(chunk(elements, max_characters=6))

    assert [c.text for c in chunks] == expected


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
def test_token_combination_still_measures_complete_text(chunk):
    elements = [Title(text) for text in ["hello", "world", "🙂🙂", "hello", "world"]]

    chunks = list(
        chunk(elements, max_tokens=7, tokenizer="cl100k_base", combine_text_under_n_chars=7)
    )

    assert [c.text for c in chunks] == ["hello\n\nworld", "🙂🙂\n\nhello", "world"]


@pytest.mark.parametrize("chunk", [chunk_by_title, iter_chunks_by_title])
def test_custom_measurement_keeps_its_existing_combination_limits(chunk, monkeypatch):
    class CustomOptions(title._ByTitleChunkingOptions):
        def measure(self, text):
            return 2 * len(text)

    monkeypatch.setattr(title, "_ByTitleChunkingOptions", CustomOptions)

    chunks = list(chunk([Title("aa"), Title("bb"), Title("cc")], max_characters=10))

    assert [c.text for c in chunks] == ["aa", "bb", "cc"]


def test_different_prechunk_options_preserve_already_accumulated_sections():
    opts = ChunkingOptions(max_characters=10, combine_text_under_n_chars=10)
    other_opts = ChunkingOptions(max_characters=1)
    pre_chunks = [
        PreChunk([Title(text)], overlap_prefix="", opts=options)
        for text, options in [("aa", opts), ("bb", opts), ("cc", other_opts), ("dd", opts)]
    ]

    combined = list(PreChunkCombiner(pre_chunks, opts).iter_combined_pre_chunks())

    assert [p._text for p in combined] == ["aa\n\nbb\n\ncc", "dd"]


def test_custom_prechunks_retain_their_combination_predicate():
    class IsolatedPreChunk(PreChunk):
        def can_combine(self, pre_chunk):
            return False

    opts = ChunkingOptions(max_characters=100, combine_text_under_n_chars=100)
    pre_chunks = [
        IsolatedPreChunk([Title(text)], overlap_prefix="", opts=opts) for text in ["a", "b", "c"]
    ]

    combined = list(PreChunkCombiner(pre_chunks, opts).iter_combined_pre_chunks())

    assert combined == pre_chunks


def test_custom_prechunk_transition_keeps_existing_merge_semantics():
    class DisplayPreChunk(PreChunk):
        def _iter_text_segments(self):
            yield "custom display when this pre-chunk stands alone"

    opts = ChunkingOptions(max_characters=10, combine_text_under_n_chars=10)
    pre_chunks = [
        PreChunk([Title("aa")], overlap_prefix="", opts=opts),
        PreChunk([Title("bb")], overlap_prefix="", opts=opts),
        DisplayPreChunk([Title("cc")], overlap_prefix="", opts=opts),
        PreChunk([Title("dd")], overlap_prefix="", opts=opts),
    ]

    combined = list(PreChunkCombiner(pre_chunks, opts).iter_combined_pre_chunks())

    assert [p._text for p in combined] == ["aa\n\nbb\n\ncc", "dd"]
