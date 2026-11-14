import copy

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, Image, Text


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
def test_provenance_consolidation_inspects_each_record_a_bounded_number_of_times(chunk):
    inspections = 0

    class CountedRecord(dict):
        def items(self):
            nonlocal inspections
            inspections += 1
            return super().items()

    elements = [
        Text(
            "x",
            metadata=ElementMetadata(
                enrichment_origins={
                    "text": [CountedRecord(type="ocr", provider="fixture", model=str(i))]
                }
            ),
        )
        for i in range(200)
    ]

    chunks = chunk(elements, max_characters=1000, include_orig_elements=False)

    assert len(chunks) == 1
    assert [record["model"] for record in chunks[0].metadata.enrichment_origins["text"]] == [
        str(i) for i in range(200)
    ]
    # Includes building the deduplication keys and copying the output metadata.
    assert inspections <= 3 * len(elements)


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize("include_orig_elements", [False, True])
def test_consolidation_preserves_list_alignment_and_first_seen_record_order(
    chunk, include_orig_elements
):
    shared = {"type": "ocr", "provider": "fixture", "model": "shared"}
    later = {"type": "enrichment", "provider": "fixture", "model": "later"}
    first_metadata = ElementMetadata(
        link_texts=["repeat", "repeat"],
        link_urls=["https://example.com/1", "https://example.com/2"],
        emphasized_text_contents=["bold", "italic"],
        emphasized_text_tags=["b", "i"],
        enrichment_origins={"text": [shared, dict(reversed(list(shared.items())))]},
    )
    second_metadata = ElementMetadata(
        link_texts=[],
        link_urls=[],
        emphasized_text_contents=[],
        emphasized_text_tags=[],
        enrichment_origins={"text": [], "text_as_html": [later]},
    )
    third_metadata = ElementMetadata(
        link_texts=["final"],
        link_urls=["https://example.com/3"],
        emphasized_text_contents=["last"],
        emphasized_text_tags=["b"],
        enrichment_origins={"text": [later, shared], "text_as_html": [dict(later)]},
    )
    elements = [
        Text("first", metadata=first_metadata),
        Text("second", metadata=second_metadata),
        Text("third", metadata=third_metadata),
    ]
    before = copy.deepcopy([element.metadata.to_dict() for element in elements])

    result = chunk(elements, max_characters=1000, include_orig_elements=include_orig_elements)[
        0
    ].metadata

    assert result.link_texts == ["repeat", "repeat", "final"]
    assert result.link_urls == [f"https://example.com/{i}" for i in range(1, 4)]
    assert result.emphasized_text_contents == ["bold", "italic", "last"]
    assert result.emphasized_text_tags == ["b", "i", "b"]
    assert list(result.enrichment_origins) == ["text", "text_as_html"]
    assert result.enrichment_origins == {"text": [shared, later], "text_as_html": [later]}
    assert result.link_texts is not first_metadata.link_texts
    result.link_texts.append("downstream value")
    result.enrichment_origins["text"][0]["model"] = "downstream model"
    assert [element.metadata.to_dict() for element in elements] == before


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
def test_consolidation_keeps_empty_image_run_metadata_and_absent_fields(chunk):
    first = {"type": "ocr", "provider": "fixture", "model": "first"}
    second = {"type": "ocr", "provider": "fixture", "model": "second"}
    elements = [
        Image("", metadata=ElementMetadata(enrichment_origins={"text": [first]}, link_texts=[])),
        Image("", metadata=ElementMetadata(enrichment_origins={"text": [first, second]})),
        Text("a paragraph"),
    ]

    result = chunk(elements, max_characters=1000, include_orig_elements=False)[0].metadata

    assert result.enrichment_origins == {"text": [first, second]}
    assert result.link_texts == []
    assert result.link_urls is None
    assert result.emphasized_text_contents is None
