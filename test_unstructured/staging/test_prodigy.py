import csv
import os

import pytest

from unstructured.documents.elements import NarrativeText, Title
from unstructured.staging import prodigy


@pytest.fixture()
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


@pytest.fixture()
def valid_metadata():
    return [{"score": 0.1}, {"category": "paragraph"}]


@pytest.fixture()
def metadata_with_id():
    return [{"score": 0.1}, {"id": 1, "category": "paragraph"}]


@pytest.fixture()
def metadata_with_invalid_length():
    return [{"score": 0.1}, {"category": "paragraph"}, {"type": "text"}]


@pytest.fixture()
def output_csv_file(tmp_path):
    return os.path.join(tmp_path, "prodigy_data.csv")


def test_validate_prodigy_metadata(elements):
    validated_metadata = prodigy._validate_prodigy_metadata(elements, metadata=None)
    assert len(validated_metadata) == len(elements)
    assert all(not data for data in validated_metadata)


def test_validate_prodigy_metadata_with_valid_metadata(elements, valid_metadata):
    validated_metadata = prodigy._validate_prodigy_metadata(elements, metadata=valid_metadata)
    assert len(validated_metadata) == len(elements)


@pytest.mark.parametrize(
    ("invalid_metadata_fixture", "exception_message"),
    [
        ("metadata_with_id", 'The key "id" is not allowed with metadata parameter at index: 1'),
        (
            "metadata_with_invalid_length",
            "The length of the metadata parameter does not match with"
            " the length of the elements parameter.",
        ),
    ],
)
def test_validate_prodigy_metadata_with_invalid_metadata(
    elements,
    invalid_metadata_fixture,
    exception_message,
    request,
):
    invalid_metadata = request.getfixturevalue(invalid_metadata_fixture)
    with pytest.raises(ValueError) as validation_exception:
        prodigy._validate_prodigy_metadata(elements, invalid_metadata)
    assert str(validation_exception.value) == exception_message


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


def test_stage_csv_for_prodigy(elements, output_csv_file):
    with open(output_csv_file, "w+") as csv_file:
        prodigy_csv_string = prodigy.stage_csv_for_prodigy(elements)
        csv_file.write(prodigy_csv_string)

    fieldnames = ["text", "id"]
    with open(output_csv_file) as csv_file:
        csv_rows = csv.DictReader(csv_file)
        assert all(set(row.keys()) == set(fieldnames) for row in csv_rows)


def test_stage_csv_for_prodigy_with_metadata(elements, valid_metadata, output_csv_file):
    with open(output_csv_file, "w+") as csv_file:
        prodigy_csv_string = prodigy.stage_csv_for_prodigy(elements, valid_metadata)
        csv_file.write(prodigy_csv_string)

    fieldnames = {"text", "id"}.union(*(data.keys() for data in valid_metadata))
    fieldnames = [fieldname.lower() for fieldname in fieldnames]
    with open(output_csv_file) as csv_file:
        csv_rows = csv.DictReader(csv_file)
        assert all(set(row.keys()) == set(fieldnames) for row in csv_rows)
