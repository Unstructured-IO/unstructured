import csv
import json
import os
import pathlib
import platform
from tempfile import NamedTemporaryFile

import pandas as pd
import pytest

from unstructured.documents.elements import (
    Address,
    CheckBox,
    ElementMetadata,
    FigureCaption,
    Image,
    ListItem,
    NarrativeText,
    PageBreak,
    Text,
    Title,
)
from unstructured.partition.email import partition_email
from unstructured.partition.text import partition_text
from unstructured.staging import base


@pytest.fixture()
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
        {"text": "No Type"},
    ]

    elements = base.isd_to_elements(isd)
    assert elements == [
        NarrativeText(text="Blurb1"),
        Title(text="Blurb2"),
        ListItem(text="Blurb3"),
        ListItem(text="Blurb4"),
    ]


def test_convert_to_csv(output_csv_file):
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    with open(output_csv_file, "w+") as csv_file:
        isd_csv_string = base.convert_to_csv(elements)
        csv_file.write(isd_csv_string)

    with open(output_csv_file) as csv_file:
        csv_rows = csv.DictReader(csv_file)
        assert all(set(row.keys()) == set(base.TABLE_FIELDNAMES) for row in csv_rows)


def test_convert_to_dataframe():
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    df = base.convert_to_dataframe(elements)
    expected_df = pd.DataFrame(
        {
            "type": ["Title", "NarrativeText"],
            "text": ["Title 1", "Narrative 1"],
        },
    )
    assert df.type.equals(expected_df.type) is True
    assert df.text.equals(expected_df.text) is True


def test_convert_to_dataframe_maintains_fields(
    filename="example-docs/eml/fake-email-attachment.eml",
):
    elements = partition_email(
        filename=filename,
        process_attachements=True,
        regex_metadata={"hello": r"Hello", "punc": r"[!]"},
    )
    df = base.convert_to_dataframe(elements)
    for element in elements:
        metadata = element.metadata.to_dict()
        for key in metadata:
            if not key.startswith("regex_metadata"):
                assert key in df.columns

    assert "regex_metadata_hello" in df.columns
    assert "regex_metadata_punc" in df.columns


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Posix Paths are not available on Windows",
)
def test_convert_to_isd_serializes_with_posix_paths():
    metadata = ElementMetadata(filename=pathlib.PosixPath("../../fake-file.txt"))
    elements = [
        Title(text="Title 1", metadata=metadata),
        NarrativeText(text="Narrative 1", metadata=metadata),
    ]
    output = base.convert_to_isd(elements)
    # NOTE(robinson) - json.dumps should run without raising an exception
    json.dumps(output)


def test_all_elements_preserved_when_serialized():
    metadata = ElementMetadata(filename="fake-file.txt")
    elements = [
        Address(text="address", metadata=metadata, element_id="1"),
        CheckBox(checked=True, metadata=metadata, element_id="2"),
        FigureCaption(text="caption", metadata=metadata, element_id="3"),
        Title(text="title", metadata=metadata, element_id="4"),
        NarrativeText(text="narrative", metadata=metadata, element_id="5"),
        ListItem(text="list", metadata=metadata, element_id="6"),
        Image(text="image", metadata=metadata, element_id="7"),
        Text(text="text", metadata=metadata, element_id="8"),
        PageBreak(text=""),
    ]

    isd = base.convert_to_isd(elements)
    assert base.convert_to_isd(base.isd_to_elements(isd)) == isd


def test_serialized_deserialize_elements_to_json(tmpdir):
    filename = os.path.join(tmpdir, "fake-elements.json")
    metadata = ElementMetadata(filename="fake-file.txt")
    elements = [
        Address(text="address", metadata=metadata, element_id="1"),
        CheckBox(checked=True, metadata=metadata, element_id="2"),
        FigureCaption(text="caption", metadata=metadata, element_id="3"),
        Title(text="title", metadata=metadata, element_id="4"),
        NarrativeText(text="narrative", metadata=metadata, element_id="5"),
        ListItem(text="list", metadata=metadata, element_id="6"),
        Image(text="image", metadata=metadata, element_id="7"),
        Text(text="text", metadata=metadata, element_id="8"),
        PageBreak(text=""),
    ]

    base.elements_to_json(elements, filename=filename)
    new_elements_filename = base.elements_from_json(filename=filename)
    assert elements == new_elements_filename

    elements_str = base.elements_to_json(elements)
    new_elements_text = base.elements_from_json(text=elements_str)
    assert elements == new_elements_text


def test_read_and_write_json_with_encoding(filename="example-docs/fake-text-utf-16-be.txt"):
    elements = partition_text(filename=filename)
    with NamedTemporaryFile() as tempfile:
        base.elements_to_json(elements, filename=tempfile.name, encoding="utf-16")
        new_elements_filename = base.elements_from_json(filename=tempfile.name, encoding="utf-16")
    assert elements == new_elements_filename
