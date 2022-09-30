import pytest

import unstructured.staging.prodigy as prodigy
from unstructured.documents.elements import Title, NarrativeText


@pytest.fixture
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


@pytest.fixture
def valid_metadata():
    return [{"score": 0.1}, {"category": "paragraph"}]


@pytest.fixture
def metadata_with_id():
    return [{"score": 0.1}, {"id": 1, "category": "paragraph"}]


@pytest.fixture
def metadata_with_invalid_length():
    return [{"score": 0.1}, {"category": "paragraph"}, {"type": "text"}]


def test_convert_to_prodigy_data(elements):
    prodigy_data = prodigy.stage_for_prodigy(elements)

    assert len(prodigy_data) == len(elements)

    assert prodigy_data[0]["text"] == "Title 1"
    assert "meta" in prodigy_data[0]
    assert "id" in prodigy_data[0]["meta"]
    assert prodigy_data[0]["meta"]["id"] == elements[0].id

    assert prodigy_data[1]["text"] == "Narrative 1"
    assert "meta" in prodigy_data[1]
    assert "id" in prodigy_data[1]["meta"]
    assert prodigy_data[1]["meta"]["id"] == elements[1].id


def test_convert_to_prodigy_data_with_valid_metadata(elements, valid_metadata):
    prodigy_data = prodigy.stage_for_prodigy(elements, valid_metadata)

    assert len(prodigy_data) == len(elements)

    assert prodigy_data[0]["text"] == "Title 1"
    assert "meta" in prodigy_data[0]
    assert prodigy_data[0]["meta"] == {"id": elements[0].id, **valid_metadata[0]}

    assert prodigy_data[1]["text"] == "Narrative 1"
    assert "meta" in prodigy_data[1]
    assert prodigy_data[1]["meta"] == {"id": elements[1].id, **valid_metadata[1]}


@pytest.mark.parametrize(
    "invalid_metadata_fixture, exception_message",
    [
        ("metadata_with_id", 'The key "id" is not allowed with metadata parameter at index: 1'),
        (
            "metadata_with_invalid_length",
            "The length of metadata parameter does not match with length of elements parameter.",
        ),
    ],
)
def test_convert_to_prodigy_data_with_invalid_metadata(
    elements, invalid_metadata_fixture, exception_message, request
):
    invalid_metadata = request.getfixturevalue(invalid_metadata_fixture)
    with pytest.raises(ValueError) as validation_exception:
        prodigy.stage_for_prodigy(elements, invalid_metadata)
    assert str(validation_exception.value) == exception_message
