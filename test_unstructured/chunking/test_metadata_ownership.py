from copy import deepcopy

import pytest

from unstructured.chunking.basic import chunk_elements, iter_chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import DataSourceMetadata, ElementMetadata, Text


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize(
    "field_name",
    [
        "languages",
        "link_texts",
        "link_urls",
        "emphasized_text_contents",
        "emphasized_text_tags",
        "sent_to",
    ],
)
def test_split_chunk_list_metadata_belongs_to_each_chunk(chunker, field_name):
    metadata = ElementMetadata(filename="source.txt", page_number=2)
    setattr(metadata, field_name, ["original"])
    source = Text("alpha bravo charlie delta echo foxtrot golf hotel", metadata=metadata)

    chunks = chunker([source], max_characters=14)
    assert len(chunks) >= 3
    getattr(chunks[0].metadata, field_name).append("first-only")

    assert all(getattr(chunk.metadata, field_name) == ["original"] for chunk in chunks[1:])
    assert getattr(source.metadata, field_name) == ["original"]
    assert all(chunk.metadata.filename == "source.txt" for chunk in chunks)
    assert all(chunk.metadata.page_number == 2 for chunk in chunks)


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
def test_split_chunk_nested_source_metadata_is_independent(chunker):
    data_source = DataSourceMetadata(
        record_locator={"paths": ["original"]},
        permissions_data=[{"roles": ["reader"]}],
    )
    source = Text(
        "alpha bravo charlie delta echo foxtrot golf hotel",
        metadata=ElementMetadata(data_source=data_source),
    )
    expected = deepcopy(data_source)

    chunks = chunker([source], max_characters=14)
    assert len(chunks) >= 3
    chunks[0].metadata.data_source.record_locator["paths"].append("first-only")
    chunks[0].metadata.data_source.permissions_data[0]["roles"].append("writer")

    assert source.metadata.data_source == expected
    assert all(chunk.metadata.data_source == expected for chunk in chunks[1:])


def test_streamed_chunk_metadata_cannot_change_chunks_not_yet_emitted():
    source = Text(
        "alpha bravo charlie delta echo foxtrot golf hotel",
        metadata=ElementMetadata(languages=["eng"]),
    )
    chunks = iter_chunk_elements([source], max_characters=14)

    first = next(chunks)
    first.metadata.languages.append("fra")
    remainder = list(chunks)

    assert remainder
    assert all(chunk.metadata.languages == ["eng"] for chunk in remainder)


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
def test_chunk_metadata_copy_keeps_original_elements_as_references(chunker):
    source = Text(
        "alpha bravo charlie delta echo foxtrot golf hotel",
        metadata=ElementMetadata(languages=["eng"]),
    )

    chunks = chunker([source], max_characters=14)

    assert len(chunks) >= 3
    assert all(chunk.metadata.orig_elements[0] is source for chunk in chunks)
    assert all(chunk.metadata.orig_elements is chunks[0].metadata.orig_elements for chunk in chunks)
    without_originals = chunker([source], max_characters=14, include_orig_elements=False)
    assert all(chunk.metadata.orig_elements is None for chunk in without_originals)
