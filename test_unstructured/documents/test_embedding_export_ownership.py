"""Vector exports must be independent snapshots of their source elements."""

import pytest

from unstructured.documents.elements import NarrativeText, TableChunk, Title
from unstructured.staging.base import elements_to_dicts


@pytest.mark.parametrize("element_cls", [NarrativeText, Title, TableChunk])
def test_exported_embedding_can_be_changed_without_mutating_source(element_cls):
    element = element_cls("Document content", embeddings=[0.1, 0.2, 0.3])

    exported = element.to_dict()
    exported["embeddings"][0] = 9.0

    assert element.embeddings == [0.1, 0.2, 0.3]


@pytest.mark.parametrize("element_cls", [NarrativeText, Title, TableChunk])
def test_later_vector_updates_do_not_change_an_existing_export(element_cls):
    element = element_cls("Document content", embeddings=[0.1, 0.2, 0.3])

    exported = element.to_dict()
    element.embeddings.append(0.4)

    assert exported["embeddings"] == [0.1, 0.2, 0.3]


def test_batch_exports_do_not_share_vectors_with_other_exports_or_sources():
    vector = [0.1, 0.2]
    first = NarrativeText("First", embeddings=vector)
    second = NarrativeText("Second", embeddings=vector)

    exported = elements_to_dicts([first, second])
    exported[0]["embeddings"].clear()

    assert exported[1]["embeddings"] == [0.1, 0.2]
    assert first.embeddings == second.embeddings == vector == [0.1, 0.2]


@pytest.mark.parametrize("embeddings", [None, []])
def test_absent_and_empty_embeddings_keep_their_serialization_shape(embeddings):
    assert "embeddings" not in NarrativeText("Content", embeddings=embeddings).to_dict()
