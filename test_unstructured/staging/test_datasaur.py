import pytest

from unstructured.documents.elements import Text
from unstructured.staging import datasaur


def test_stage_for_datasaur():
    elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
    result = datasaur.stage_for_datasaur(elements)
    assert result[0]["text"] == "Text 1"
    assert result[0]["entities"] == []
    assert result[1]["text"] == "Text 2"
    assert result[1]["entities"] == []
    assert result[2]["text"] == "Text 3"
    assert result[2]["entities"] == []


def test_stage_for_datasaur_with_entities():
    elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
    entities = [[{"text": "Matt", "type": "PER", "start_idx": 11, "end_idx": 15}], [], []]

    result = datasaur.stage_for_datasaur(elements, entities=entities)
    assert result[0]["text"] == "Text 1"
    assert result[0]["entities"] == entities[0]
    assert result[1]["text"] == "Text 2"
    assert result[1]["entities"] == entities[1]
    assert result[2]["text"] == "Text 3"
    assert result[2]["entities"] == entities[2]


def test_datasaur_raises_with_missing_entity_text():
    with pytest.raises(ValueError):
        elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
        datasaur.stage_for_datasaur(elements, entities=[{"bad_key": "text"}])


def test_datasaur_raises_with_missing_key():
    entities = [[{"text": "Matt", "type": "PER", "start_idx": 11}], [], []]

    with pytest.raises(ValueError):
        elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
        datasaur.stage_for_datasaur(elements, entities=entities)


def test_datasaur_raises_with_bad_type():
    entities = [[{"text": "Matt", "type": "PER", "start_idx": 11, "end_idx": "15"}], [], []]

    with pytest.raises(ValueError):
        elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
        datasaur.stage_for_datasaur(elements, entities=entities)


def test_datasaur_raises_with_wrong_length():
    entities = [[{"text": "Matt", "type": "PER", "start_idx": 11, "end_idx": 15}], []]

    with pytest.raises(ValueError):
        elements = [Text("Text 1"), Text("Text 2"), Text("Text 3")]
        datasaur.stage_for_datasaur(elements, entities=entities)
