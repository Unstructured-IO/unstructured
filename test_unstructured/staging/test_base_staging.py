import csv
import json
import os
import pathlib
import pytest

import pandas as pd

import unstructured.staging.base as base

from unstructured.documents.elements import ElementMetadata, Title, NarrativeText, ListItem


@pytest.fixture
def output_csv_file(tmp_path):
    return os.path.join(tmp_path, "isd_data.csv")


def test_convert_to_isd():
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    isd = base.convert_to_isd(elements)

    assert isd[0]["text"] == "Title 1"
    assert isd[0]["type"] == "Title"

    assert isd[1]["text"] == "Narrative 1"
    assert isd[1]["type"] == "NarrativeText"


def test_isd_to_elements():
    isd = [
        {"text": "Blurb1", "type": "NarrativeText"},
        {"text": "Blurb2", "type": "Title"},
        {"text": "Blurb3", "type": "ListItem"},
        {"text": "Blurb4", "type": "BulletedText"},
    ]

    elements = base.isd_to_elements(isd)
    assert elements == [
        NarrativeText(text="Blurb1"),
        Title(text="Blurb2"),
        ListItem(text="Blurb3"),
        ListItem(text="Blurb4"),
    ]


def test_convert_to_isd_csv(output_csv_file):
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    with open(output_csv_file, "w+") as csv_file:
        isd_csv_string = base.convert_to_isd_csv(elements)
        csv_file.write(isd_csv_string)

    with open(output_csv_file, "r") as csv_file:
        csv_rows = csv.DictReader(csv_file)
        assert all(set(row.keys()) == set(base.TABLE_FIELDNAMES) for row in csv_rows)


def test_convert_to_dataframe():
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    df = base.convert_to_dataframe(elements)
    expected_df = pd.DataFrame(
        {
            "type": ["Title", "NarrativeText"],
            "text": ["Title 1", "Narrative 1"],
        }
    )
    assert df.type.equals(expected_df.type) is True
    assert df.text.equals(expected_df.text) is True


def test_convert_to_isd_serializes_with_posix_paths():
    metadata = ElementMetadata(filename=pathlib.PosixPath("../../fake-file.txt"))
    elements = [
        Title(text="Title 1", metadata=metadata),
        NarrativeText(text="Narrative 1", metadata=metadata),
    ]
    output = base.convert_to_isd(elements)
    # NOTE(robinson) - json.dumps should run without raising an exception
    json.dumps(output)
