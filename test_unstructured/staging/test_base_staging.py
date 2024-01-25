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
    CoordinatesMetadata,
    CoordinateSystem,
    DataSourceMetadata,
    ElementMetadata,
    ElementType,
    FigureCaption,
    Image,
    Link,
    ListItem,
    NarrativeText,
    PageBreak,
    RegexMetadata,
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
    assert isd[0]["type"] == ElementType.TITLE

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


def test_default_pandas_dtypes():
    """
    Make sure that all the values that can exist on an element have a corresponding dtype
    mapped in the dict returned by get_default_pandas_dtypes()
    """
    full_element = Text(
        text="some text",
        element_id="123",
        coordinates=((1, 2), (3, 4)),
        coordinate_system=CoordinateSystem(width=12.3, height=99.4),
        detection_origin="some origin",
        embeddings=[1.1, 2.2, 3.3, 4.4],
        metadata=ElementMetadata(
            coordinates=CoordinatesMetadata(
                points=((1, 2), (3, 4)),
                system=CoordinateSystem(width=12.3, height=99.4),
            ),
            data_source=DataSourceMetadata(
                url="http://mysite.com",
                version="123",
                record_locator={"some": "data", "value": 3},
                date_created="then",
                date_processed="now",
                date_modified="before",
                permissions_data=[{"data": 1}, {"data": 2}],
            ),
            filename="filename",
            file_directory="file_directory",
            last_modified="last_modified",
            filetype="filetype",
            attached_to_filename="attached_to_filename",
            parent_id="parent_id",
            category_depth=1,
            image_path="image_path",
            languages=["eng", "spa"],
            page_number=1,
            page_name="page_name",
            url="url",
            link_urls=["links", "url"],
            link_texts=["links", "texts"],
            links=[Link(text="text", url="url", start_index=1)],
            sent_from=["sent", "from"],
            sent_to=["sent", "to"],
            subject="subject",
            section="section",
            header_footer_type="header_footer_type",
            emphasized_text_contents=["emphasized", "text", "contents"],
            emphasized_text_tags=["emphasized", "text", "tags"],
            text_as_html="text_as_html",
            regex_metadata={"key": [RegexMetadata(text="text", start=0, end=4)]},
            is_continuation=True,
            detection_class_prob=0.5,
        ),
    )
    element_as_dict = full_element.to_dict()
    element_as_dict.update(
        base.flatten_dict(
            element_as_dict.pop("metadata"),
            keys_to_omit=["data_source_record_locator"],
        ),
    )
    flattened_element_keys = element_as_dict.keys()
    default_dtypes = base.get_default_pandas_dtypes()
    dtype_keys = default_dtypes.keys()
    for key in flattened_element_keys:
        assert key in dtype_keys


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


def test_read_and_write_json_with_encoding(
    filename="example-docs/fake-text-utf-16-be.txt",
):
    elements = partition_text(filename=filename)
    with NamedTemporaryFile() as tempfile:
        base.elements_to_json(elements, filename=tempfile.name, encoding="utf-16")
        new_elements_filename = base.elements_from_json(
            filename=tempfile.name,
            encoding="utf-16",
        )
    assert elements == new_elements_filename


def test_filter_element_types_with_include_element_type(
    filename="example-docs/fake-text.txt",
):
    element_types = [Title]
    elements = partition_text(
        filename=filename,
        include_metadata=False,
    )
    elements = base.filter_element_types(
        elements=elements,
        include_element_types=element_types,
    )
    for element in elements:
        assert type(element) in element_types


def test_filter_element_types_with_exclude_element_type(
    filename="example-docs/fake-text.txt",
):
    element_types = [Title]
    elements = partition_text(
        filename=filename,
        include_metadata=False,
    )
    elements = base.filter_element_types(
        elements=elements,
        exclude_element_types=element_types,
    )
    for element in elements:
        assert type(element) not in element_types


def test_filter_element_types_with_exclude_and_include_element_type(
    filename="example-docs/fake-text.txt",
):
    element_types = [Title]
    elements = partition_text(
        filename=filename,
        include_metadata=False,
    )
    with pytest.raises(ValueError):
        elements = base.filter_element_types(
            elements=elements,
            exclude_element_types=element_types,
            include_element_types=element_types,
        )


def test_convert_to_coco():
    elements = [
        Text(
            text="some text",
            element_id="123",
            detection_origin="some origin",
            embeddings=[1.1, 2.2, 3.3, 4.4],
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=((1, 2), (1, 4), (3, 4), (3, 2)),
                    system=CoordinateSystem(width=12.3, height=99.4),
                ),
                data_source=DataSourceMetadata(
                    url="http://mysite.com",
                    version="123",
                    record_locator={"some": "data", "value": 3},
                    date_created="then",
                    date_processed="now",
                    date_modified="before",
                    permissions_data=[{"data": 1}, {"data": 2}],
                ),
                filename="filename",
                file_directory="file_directory",
                last_modified="last_modified",
                filetype="filetype",
                attached_to_filename="attached_to_filename",
                parent_id="parent_id",
                category_depth=1,
                image_path="image_path",
                languages=["eng", "spa"],
                page_number=1,
                page_name="page_name",
                url="url",
                link_urls=["links", "url"],
                link_texts=["links", "texts"],
                links=[Link(text="text", url="url", start_index=1)],
                sent_from=["sent", "from"],
                sent_to=["sent", "to"],
                subject="subject",
                section="section",
                header_footer_type="header_footer_type",
                emphasized_text_contents=["emphasized", "text", "contents"],
                emphasized_text_tags=["emphasized", "text", "tags"],
                text_as_html="text_as_html",
                regex_metadata={"key": [RegexMetadata(text="text", start=0, end=4)]},
                is_continuation=True,
                detection_class_prob=0.5,
            ),
        )
    ]
    missing_elements = [
        Text(
            text="some text",
            element_id="123",
            detection_origin="some origin",
            embeddings=[1.1, 2.2, 3.3, 4.4],
            metadata=ElementMetadata(
                data_source=DataSourceMetadata(
                    url="http://mysite.com",
                    version="123",
                    record_locator={"some": "data", "value": 3},
                    date_created="then",
                    date_processed="now",
                    date_modified="before",
                    permissions_data=[{"data": 1}, {"data": 2}],
                ),
                filename="filename",
                file_directory="file_directory",
                last_modified="last_modified",
                filetype="filetype",
                attached_to_filename="attached_to_filename",
                parent_id="parent_id",
                category_depth=1,
                image_path="image_path",
                languages=["eng", "spa"],
                page_number=1,
                page_name="page_name",
                url="url",
                link_urls=["links", "url"],
                link_texts=["links", "texts"],
                links=[Link(text="text", url="url", start_index=1)],
                sent_from=["sent", "from"],
                sent_to=["sent", "to"],
                subject="subject",
                section="section",
                header_footer_type="header_footer_type",
                emphasized_text_contents=["emphasized", "text", "contents"],
                emphasized_text_tags=["emphasized", "text", "tags"],
                text_as_html="text_as_html",
                regex_metadata={"key": [RegexMetadata(text="text", start=0, end=4)]},
                is_continuation=True,
                detection_class_prob=0.5,
            ),
        )
    ]
    full_coco = base.convert_to_coco(elements)
    limited_coco = base.convert_to_coco(missing_elements)
    assert full_coco["annotations"][0]["area"]
    assert limited_coco["annotations"][0]["area"] is None


def test_flatten_dict():
    """Flattening a simple dictionary"""
    dictionary = {"a": 1, "b": 2, "c": 3}
    expected_result = {"a": 1, "b": 2, "c": 3}
    assert base.flatten_dict(dictionary) == expected_result


def test_flatten_nested_dict():
    """Flattening a nested dictionary"""
    dictionary = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
    expected_result = {"a": 1, "b_c": 2, "b_d": 3, "e": 4}
    assert base.flatten_dict(dictionary) == expected_result


def test_flatten_dict_with_tuples():
    """Flattening a dictionary with tuples"""
    dictionary = {"a": 1, "b": (2, 3, 4), "c": {"d": 5, "e": (6, 7)}}
    expected_result = {"a": 1, "b": (2, 3, 4), "c_d": 5, "c_e": (6, 7)}
    assert base.flatten_dict(dictionary) == expected_result


def test_flatten_dict_with_lists():
    """Flattening a dictionary with lists"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": [6, 7]}}
    expected_result = {"a": 1, "b": [2, 3, 4], "c_d": 5, "c_e": [6, 7]}
    assert base.flatten_dict(dictionary) == expected_result


def test_flatten_dict_with_omit_keys():
    """Flattening a dictionary with keys to omit"""
    dictionary = {"a": 1, "b": {"c": 2, "d": 3}, "e": 3}
    keys_to_omit = ["b"]
    expected_result = {"a": 1, "b": {"c": 2, "d": 3}, "e": 3}
    assert base.flatten_dict(dictionary, keys_to_omit=keys_to_omit) == expected_result


def test_flatten_dict_alt_separator():
    """Flattening a dictionary with separator other than "_" """
    dictionary = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
    separator = "-"
    expected_result = {"a": 1, "b-c": 2, "b-d": 3, "e": 4}
    assert base.flatten_dict(dictionary, separator=separator) == expected_result


def test_flatten_dict_flatten_tuple():
    """Flattening a dictionary with flatten_lists set to True, to flatten tuples"""
    dictionary = {"a": 1, "b": (2, 3, 4), "c": {"d": 5, "e": (6, 7)}}
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c_d": 5, "c_e_0": 6, "c_e_1": 7}
    assert base.flatten_dict(dictionary, flatten_lists=True) == expected_result


def test_flatten_dict_flatten_list():
    """Flattening a dictionary with flatten_lists set to True"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": [6, 7]}}
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c_d": 5, "c_e_0": 6, "c_e_1": 7}
    assert base.flatten_dict(dictionary, flatten_lists=True) == expected_result


def test_flatten_dict_flatten_list_omit_keys():
    """Flattening a dictionary with flatten_lists set to True and also omitting keys"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": [6, 7]}}
    keys_to_omit = ["c"]
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c": {"d": 5, "e": [6, 7]}}
    assert (
        base.flatten_dict(dictionary, keys_to_omit=keys_to_omit, flatten_lists=True)
        == expected_result
    )


def test_flatten_dict_flatten_list_omit_keys_remove_none():
    """Flattening a dictionary with flatten_lists set to True and also omitting keys
    and setting remove_none to True"""
    dictionary = {"a": None, "b": [2, 3, 4], "c": {"d": None, "e": [6, 7]}}
    keys_to_omit = ["c"]
    expected_result = {"b_0": 2, "b_1": 3, "b_2": 4, "c": {"d": None, "e": [6, 7]}}
    assert (
        base.flatten_dict(
            dictionary, keys_to_omit=keys_to_omit, flatten_lists=True, remove_none=True
        )
        == expected_result
    )


def test_flatten_dict_flatten_list_remove_none():
    """Flattening a dictionary with flatten_lists set to True and setting remove_none to True"""
    dictionary = {"a": None, "b": [2, 3, 4], "c": {"d": None, "e": [6, 7]}}
    expected_result = {"b_0": 2, "b_1": 3, "b_2": 4, "c_e_0": 6, "c_e_1": 7}
    assert base.flatten_dict(dictionary, flatten_lists=True, remove_none=True) == expected_result


def test_flatten_dict_flatten_list_none_in_list_remove_none():
    """Flattening a dictionary with flatten_lists and remove_none set to True and None in list"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": None, "e": [6, None]}}
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c_e_0": 6}
    assert base.flatten_dict(dictionary, flatten_lists=True, remove_none=True) == expected_result


def test_flatten_dict_flatten_list_omit_keys2():
    """Flattening a dictionary with flatten_lists set to True and also omitting keys"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": [6, 7]}}
    keys_to_omit = ["b"]
    expected_result = {"a": 1, "b": [2, 3, 4], "c_d": 5, "c_e_0": 6, "c_e_1": 7}
    assert (
        base.flatten_dict(dictionary, keys_to_omit=keys_to_omit, flatten_lists=True)
        == expected_result
    )


def test_flatten_dict_flatten_list_omit_keys3():
    """Flattening a dictionary with flatten_lists set to True and also omitting nested keys"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": [6, 7]}}
    keys_to_omit = ["c_e"]
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c_d": 5, "c_e": [6, 7]}
    assert (
        base.flatten_dict(dictionary, keys_to_omit=keys_to_omit, flatten_lists=True)
        == expected_result
    )


def test_flatten_dict_flatten_list_omit_keys4():
    """Flattening a dictionary with flatten_lists set to True and also omitting nested keys"""
    dictionary = {"a": 1, "b": [2, 3, 4], "c": {"d": 5, "e": {"f": 6, "g": 7}}}
    keys_to_omit = ["c_e"]
    expected_result = {"a": 1, "b_0": 2, "b_1": 3, "b_2": 4, "c_d": 5, "c_e": {"f": 6, "g": 7}}
    assert (
        base.flatten_dict(dictionary, keys_to_omit=keys_to_omit, flatten_lists=True)
        == expected_result
    )


def test_flatten_empty_dict():
    """Flattening an empty dictionary"""
    dictionary = {}
    expected_result = {}
    assert base.flatten_dict(dictionary) == expected_result


def test_flatten_dict_empty_lists():
    """Flattening a dictionary with empty lists"""
    dictionary = {"a": [], "b": {"c": []}}
    expected_result = {"a": [], "b_c": []}
    assert base.flatten_dict(dictionary) == expected_result
