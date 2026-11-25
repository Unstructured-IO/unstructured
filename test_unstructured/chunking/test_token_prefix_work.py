"""Token chunking should not repeatedly encode a prefix just measured for admission."""

from collections.abc import Callable, Iterable

import pytest

from unstructured.chunking.base import ChunkingOptions, PreChunkBuilder, TokenCounter
from unstructured.chunking.basic import chunk_elements, iter_chunk_elements
from unstructured.chunking.title import chunk_by_title, iter_chunks_by_title
from unstructured.documents.elements import Element, ElementMetadata, Image, Text

pytest.importorskip("tiktoken")


@pytest.mark.parametrize(
    "chunker", [chunk_elements, chunk_by_title, iter_chunk_elements, iter_chunks_by_title]
)
def test_token_chunking_bounds_repeated_prefix_encoding(
    chunker: Callable[..., Iterable[Element]], monkeypatch: pytest.MonkeyPatch
) -> None:
    count = TokenCounter.count
    calls = 0

    def counted(self: TokenCounter, text: str) -> int:
        nonlocal calls
        calls += 1
        return count(self, text)

    monkeypatch.setattr(TokenCounter, "count", counted)
    elements = [
        Text(
            f"Record {i} describes the observed document structure and its readable content.",
            metadata=ElementMetadata(filename="source.pdf", languages=["eng"]),
        )
        for i in range(200)
    ]

    chunks = list(
        chunker(
            elements,
            max_tokens=1024,
            tokenizer="cl100k_base",
            include_orig_elements=False,
        )
    )

    # Allow the independent final-chunk and combination checks while excluding a second
    # encoding of essentially every growing prefix during element admission.
    assert calls <= len(elements) + 10 * len(chunks)
    assert "\n\n".join(str(chunk) for chunk in chunks) == "\n\n".join(map(str, elements))
    assert all(count(TokenCounter("cl100k_base"), str(chunk)) <= 1024 for chunk in chunks)
    assert all(chunk.metadata.filename == "source.pdf" for chunk in chunks)
    assert all(chunk.metadata.languages == ["eng"] for chunk in chunks)
    assert all(chunk.metadata.orig_elements is None for chunk in chunks)


def test_rejected_trial_does_not_change_the_current_prefix_count() -> None:
    opts = ChunkingOptions.new(max_tokens=12, tokenizer="cl100k_base")
    builder = PreChunkBuilder(opts)
    builder.add_element(Text("one two"))

    assert not builder.will_fit(Text("a long candidate " * 30))
    assert builder._text_length == opts.measure("one two")
    assert builder.will_fit(Text("three four"))
    builder.add_element(Text("five six"))

    assert builder._text_length == opts.measure("one two\n\nfive six")
    assert next(builder.flush())._text == "one two\n\nfive six"


def test_token_prefix_count_follows_changed_text_and_flush_overlap() -> None:
    opts = ChunkingOptions.new(max_tokens=20, tokenizer="cl100k_base", overlap=3, overlap_all=True)
    builder = PreChunkBuilder(opts)
    builder.add_element(Text("A short first paragraph."))
    candidate = Text("one two")
    assert builder.will_fit(candidate)
    candidate.text = "different words now"
    builder.add_element(candidate)

    combined = "A short first paragraph.\n\ndifferent words now"
    assert builder._text_length == opts.measure(combined)
    first = next(builder.flush())
    builder.add_element(Text("next paragraph"))

    assert builder._text_length == opts.measure(first.overlap_tail + "\n\nnext paragraph")
    assert next(builder.flush())._text == first.overlap_tail + "\n\nnext paragraph"


def test_textless_elements_do_not_reencode_an_unchanged_token_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    count = TokenCounter.count
    calls = 0

    def counted(self: TokenCounter, text: str) -> int:
        nonlocal calls
        calls += 1
        return count(self, text)

    monkeypatch.setattr(TokenCounter, "count", counted)
    source = Text("The document contains illustrations without extracted text.")
    elements = [source, *(Image("") for _ in range(100))]

    chunks = chunk_elements(elements, max_tokens=128, tokenizer="cl100k_base")

    assert len(chunks) == 1
    assert str(chunks[0]) == str(source)
    assert chunks[0].metadata.orig_elements == elements
    assert calls <= 10


def test_character_chunking_does_not_call_the_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_count(self: TokenCounter, text: str) -> int:
        raise AssertionError("character chunking must not tokenize")

    monkeypatch.setattr(TokenCounter, "count", unexpected_count)

    chunks = chunk_elements([Text("one two"), Text("three four")], max_characters=10)

    assert [str(chunk) for chunk in chunks] == ["one two", "three four"]
