import os
import pytest
import csv

import unstructured.staging.base as base

from unstructured.documents.elements import Title, NarrativeText


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


def test_convert_to_isd_csv(output_csv_file):

    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    with open(output_csv_file, "w+") as csv_file:
        isd_csv_string = base.convert_to_isd_csv(elements)
        csv_file.write(isd_csv_string)

    fieldnames = ["type", "text"]
    with open(output_csv_file, "r") as csv_file:
        csv_rows = csv.DictReader(csv_file)
        assert all(set(row.keys()) == set(fieldnames) for row in csv_rows)
