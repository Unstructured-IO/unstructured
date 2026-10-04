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


@pytest.mark.parametrize(
    "metadata",
    [[{}, {}], [{"category": "title"}, {"category": "paragraph"}]],
)
def test_convert_to_prodigy_data_preserves_metadata(elements, metadata):
    original_metadata = [metadatum.copy() for metadatum in metadata]

    prodigy_data = prodigy.stage_for_prodigy(elements, metadata)

    assert metadata == original_metadata
    assert [data["meta"] for data in prodigy_data] == [
        {**metadatum, "id": element.id} for element, metadatum in zip(elements, original_metadata)
    ]

    prodigy_data[0]["meta"]["category"] = "changed"
    assert metadata == original_metadata


@pytest.mark.parametrize("stage", [prodigy.stage_for_prodigy, prodigy.stage_csv_for_prodigy])
def test_convert_to_prodigy_data_allows_metadata_reuse(elements, valid_metadata, stage):
    expected = stage(elements, [metadatum.copy() for metadatum in valid_metadata])

    prodigy.stage_for_prodigy(elements, valid_metadata)

    assert stage(elements, valid_metadata) == expected


@pytest.mark.parametrize("shared_metadata", [{}, {"category": "paragraph"}])
def test_convert_to_prodigy_data_with_shared_metadata(elements, shared_metadata):
    original_metadata = shared_metadata.copy()

    prodigy_data = prodigy.stage_for_prodigy(elements, [shared_metadata] * len(elements))

    assert [data["meta"]["id"] for data in prodigy_data] == [element.id for element in elements]
    prodigy_data[0]["meta"]["category"] = "changed"
    assert prodigy_data[1]["meta"] == {**original_metadata, "id": elements[1].id}
    assert shared_metadata == original_metadata


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
