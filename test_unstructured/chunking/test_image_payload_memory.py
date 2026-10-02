"""Check payload release and metadata parity against the identity-preserving path."""

import random
import weakref

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    ElementMetadata,
    Image,
    NarrativeText,
    PageBreak,
    Table,
    Title,
)


def _elements(seed):
    randomizer = random.Random(seed)
    elements = []
    for index in range(50):
        kind = randomizer.choice([Image, Image, Image, NarrativeText, Title, Table, PageBreak])
        text = "" if kind in (Image, PageBreak) else (" text" * randomizer.randrange(1, 30))
        metadata = ElementMetadata(
            filename=f"file-{index % 3}.pdf",
            page_number=index // 10,
            image_base64="payload" * 100 if kind is Image else None,
            languages=["eng", "spa"] if index % 2 else ["spa"],
            link_texts=[str(index)],
            link_urls=[f"https://example.org/{index}"],
            text_as_html=["", "  ", " <p>content</p> "][index % 3],
            enrichment_origins={"model": [{"id": str(index % 4), "version": "1"}]},
        )
        elements.append(kind(text=text, metadata=metadata, element_id=f"input-{index}"))
    return elements


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize("overlap", [0, 15])
def test_excluding_originals_preserves_chunk_boundaries_and_metadata(seed, chunker, overlap):
    elements = _elements(seed)
    kwargs = {
        "max_characters": 120,
        "new_after_n_chars": 80,
        "overlap": overlap,
        "overlap_all": True,
    }
    retained = chunker(elements, include_orig_elements=True, **kwargs)
    compact = chunker(iter(elements), include_orig_elements=False, **kwargs)
    expected = [chunk.to_dict() for chunk in retained]
    actual = [chunk.to_dict() for chunk in compact]
    for values in (expected, actual):
        table_ids = {}
        for value in values:
            value.pop("element_id")
            value["metadata"].pop("orig_elements", None)
            if "table_id" in value["metadata"]:
                identifier = value["metadata"]["table_id"]
                value["metadata"]["table_id"] = table_ids.setdefault(identifier, len(table_ids))
    assert actual == expected
    for chunk in retained:
        assert all(
            any(original is element for element in elements)
            for original in chunk.metadata.orig_elements
            if isinstance(original, Image)
        )


@pytest.mark.parametrize("include_text", [False, True])
def test_empty_image_payloads_are_released_while_the_input_is_consumed(include_text):
    references = []

    def images():
        for _ in range(100):
            # Fresh payloads model a streamed image partitioner rather than a caller-owned list.
            image = Image(text="", metadata=ElementMetadata(image_base64="x" * 1024 * 1024))
            references.append(weakref.ref(image))
            assert sum(ref() is not None for ref in references) <= 2
            yield image
        if include_text:
            yield NarrativeText("the final paragraph")

    chunks = chunk_elements(images(), include_orig_elements=False)
    assert [chunk.text for chunk in chunks] == (["the final paragraph"] if include_text else [])
    assert all(reference() is None for reference in references)


def test_default_chunking_retains_empty_original_image_identity():
    image = Image(text="", metadata=ElementMetadata(image_base64="payload"))
    paragraph = NarrativeText("paragraph")
    (chunk,) = chunk_elements([image, paragraph])
    assert chunk.metadata.orig_elements[0] is image
    assert chunk.metadata.orig_elements[1] is paragraph
