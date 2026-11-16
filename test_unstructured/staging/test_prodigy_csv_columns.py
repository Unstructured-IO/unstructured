import csv
import io
from copy import deepcopy

import pytest

from unstructured.documents.elements import Text
from unstructured.staging.prodigy import stage_csv_for_prodigy, stage_for_prodigy


@pytest.mark.parametrize("key", ["ID", "Id", "iD", "text", "Text", "TEXT"])
def test_csv_metadata_cannot_overwrite_a_reserved_column_after_lowercasing(key):
    elements = [Text("first"), Text("second")]
    metadata = [{"source": "safe"}, {key: "external value"}]
    original = deepcopy(metadata)

    with pytest.raises(ValueError, match=f'"{key}".*index: 1'):
        stage_csv_for_prodigy(elements, metadata)

    assert metadata == original


@pytest.mark.parametrize(
    "metadata",
    [
        {"Tag": "first", "tag": "second"},
        {"tag": "first", "Tag": "second"},
        {"SOURCE": "first", "Source": "second"},
    ],
)
def test_csv_metadata_keys_cannot_silently_collapse_into_one_column(metadata):
    original = deepcopy(metadata)

    with pytest.raises(ValueError, match="Multiple metadata keys normalize"):
        stage_csv_for_prodigy([Text("source text")], [metadata])

    assert metadata == original


def test_matching_column_names_in_different_rows_are_valid():
    elements = [Text("first"), Text("second")]
    metadata = [{"Tag": "first tag"}, {"tag": "second tag"}]
    original = deepcopy(metadata)

    rows = list(csv.DictReader(io.StringIO(stage_csv_for_prodigy(elements, metadata))))

    assert rows == [
        {"text": element.text, "id": element.id, "tag": tag}
        for element, tag in zip(elements, ["first tag", "second tag"])
    ]
    assert metadata == original


def test_json_metadata_remains_case_sensitive():
    metadata = [{"ID": "external id", "Text": "external text", "Tag": "one", "tag": "two"}]

    output = stage_for_prodigy([Text("source text")], metadata)

    assert output[0]["text"] == "source text"
    for key in ("ID", "Text", "Tag", "tag"):
        assert output[0]["meta"][key] == metadata[0][key]


def test_csv_without_metadata_retains_the_element_columns():
    element = Text("source text")

    rows = list(csv.DictReader(io.StringIO(stage_csv_for_prodigy([element]))))

    assert rows == [{"text": element.text, "id": element.id}]
