import pandas as pd
import pytest

from unstructured.documents.elements import CheckBox, DataSourceMetadata, ElementMetadata, Text
from unstructured.staging.base import convert_to_dataframe


@pytest.mark.parametrize("set_dtypes", [False, True])
@pytest.mark.parametrize(
    ("field", "metadata_value"),
    [
        ("text", "external text"),
        ("type", "external type"),
        ("element_id", "external id"),
        ("embeddings", [9.0]),
    ],
)
def test_metadata_does_not_replace_element_columns(field, metadata_value, set_dtypes):
    element = Text(
        "source text",
        element_id="source id",
        embeddings=[1.0],
        metadata=ElementMetadata.from_dict({field: metadata_value}),
    )

    frame = convert_to_dataframe([element], set_dtypes=set_dtypes)

    assert frame.at[0, field] == element.to_dict()[field]
    assert frame.at[0, f"metadata_{field}"] == metadata_value
    assert element.metadata.to_dict()[field] == metadata_value


def test_disambiguation_preserves_existing_prefixed_metadata_names():
    metadata = {
        "text": "external text",
        "metadata_text": "first prefixed value",
        "metadata_metadata_text": "second prefixed value",
    }
    element = Text("source text", metadata=ElementMetadata.from_dict(metadata))

    frame = convert_to_dataframe([element])

    assert frame.at[0, "text"] == "source text"
    assert frame.at[0, "metadata_metadata_metadata_text"] == "external text"
    assert frame.at[0, "metadata_text"] == "first prefixed value"
    assert frame.at[0, "metadata_metadata_text"] == "second prefixed value"


@pytest.mark.parametrize("reverse", [False, True])
def test_top_level_columns_are_reserved_across_the_whole_batch(reverse):
    elements = [
        Text("source text", metadata=ElementMetadata.from_dict({"checked": "external status"})),
        CheckBox(checked=False),
    ]
    if reverse:
        elements.reverse()

    frame = convert_to_dataframe(iter(elements))
    text_row = frame[frame["type"] == "UncategorizedText"].iloc[0]
    checkbox_row = frame[frame["type"] == "CheckBox"].iloc[0]

    assert pd.isna(text_row["checked"])
    assert text_row["metadata_checked"] == "external status"
    assert checkbox_row["checked"] == False  # noqa: E712
    assert pd.isna(checkbox_row["metadata_checked"])


def test_noncolliding_metadata_keeps_its_columns_and_dtype_options():
    metadata = ElementMetadata(
        filename="source.txt",
        page_number=3,
        data_source=DataSourceMetadata(
            url="s3://bucket/source.txt", record_locator={"key": "source.txt"}
        ),
    )
    metadata.metadata_text = "already prefixed"
    element = Text("source text", metadata=metadata)

    frame = convert_to_dataframe([element], set_dtypes=True, drop_empty_cols=False)

    assert frame.at[0, "filename"] == "source.txt"
    assert frame.at[0, "page_number"] == 3
    assert str(frame["page_number"].dtype) == "Int64"
    assert frame.at[0, "data_source_url"] == "s3://bucket/source.txt"
    assert frame.at[0, "metadata_text"] == "already prefixed"
    assert frame.at[0, "data_source_record_locator"] == {"key": "source.txt"}


def test_empty_input_still_produces_an_empty_dataframe():
    assert convert_to_dataframe([]).empty
