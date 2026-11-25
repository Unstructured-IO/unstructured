import pytest

from unstructured.chunking import base
from unstructured.chunking.basic import chunk_elements, iter_chunk_elements
from unstructured.documents.elements import ElementMetadata, Image, Table, TableChunk, Text


@pytest.mark.parametrize("chunk", [chunk_elements, iter_chunk_elements])
@pytest.mark.parametrize("include_orig_elements", [True, False])
def test_table_detection_work_is_linear_for_image_runs(
    monkeypatch: pytest.MonkeyPatch, chunk, include_orig_elements: bool
):
    """Empty images don't consume the text budget, so they can form a long pre-chunk."""
    elements = [Image("", metadata=ElementMetadata(page_number=i + 1)) for i in range(300)]
    elements.append(Text("Visible text"))
    checks = 0
    original = base._element_is_table_family

    def counted(element):
        nonlocal checks
        checks += 1
        return original(element)

    monkeypatch.setattr(base, "_element_is_table_family", counted)

    chunks = list(chunk(iter(elements), include_orig_elements=include_orig_elements))

    assert [result.text for result in chunks] == ["Visible text"]
    assert chunks[0].metadata.page_number == 1
    if include_orig_elements:
        assert chunks[0].metadata.orig_elements == elements
        assert all(
            actual is expected
            for actual, expected in zip(chunks[0].metadata.orig_elements, elements)
        )
    else:
        assert chunks[0].metadata.orig_elements is None
    assert checks <= 4 * len(elements)


@pytest.mark.parametrize("table_type", [Table, TableChunk])
def test_table_detection_resets_before_flush_iterator_is_exhausted(table_type):
    builder = base.PreChunkBuilder(base.ChunkingOptions())
    table = table_type("Cell")
    builder.add_element(table)
    assert not builder.will_fit(Text("Next section"))

    flushed = builder.flush()
    assert next(flushed)._elements == [table]
    assert builder.will_fit(Text("Next section"))
    builder.add_element(Text("Next section"))
    assert builder.will_fit(Text("More text"))
    assert not builder.will_fit(table_type("Another table"))
    assert list(flushed) == []
