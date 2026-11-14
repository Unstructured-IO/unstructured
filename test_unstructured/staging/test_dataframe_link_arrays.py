"""Explicit pandas dtypes must retain the list-valued link metadata."""

import json
from copy import deepcopy

import pandas as pd
import pytest

from unstructured.documents.elements import ElementMetadata, Text
from unstructured.staging.base import convert_to_dataframe


def make_element(urls: list[str]) -> Text:
    """Create matching link URLs, captions, and offsets on one text element."""
    return Text(
        "alpha beta",
        element_id="sample",
        metadata=ElementMetadata(
            link_urls=urls,
            link_texts=["alpha", "beta"][: len(urls)],
            link_start_indexes=[0, 6][: len(urls)],
            page_number=2,
        ),
    )


@pytest.mark.parametrize(
    "urls", [["https://a.example"], ["https://a.example/q?'x'", "https://例.example"]]
)
@pytest.mark.parametrize("set_dtypes", [False, True])
def test_typed_dataframe_keeps_link_lists_and_source_metadata(urls, set_dtypes):
    element = make_element(urls)
    before = deepcopy(element.to_dict())

    frame = convert_to_dataframe([element], set_dtypes=set_dtypes)

    assert frame.loc[0, "link_urls"] == urls
    assert frame["link_urls"].dtype == object
    assert frame.loc[0, "page_number"] == 2
    assert element.to_dict() == before


def test_missing_links_stay_missing_alongside_real_link_lists():
    frame = convert_to_dataframe(
        [Text("no links"), make_element(["https://a.example"])], set_dtypes=True
    )

    assert pd.isna(frame.loc[0, "link_urls"])
    assert frame.loc[1, "link_urls"] == ["https://a.example"]


def test_exploding_links_keeps_urls_aligned_with_their_captions_and_offsets():
    frame = convert_to_dataframe(
        [make_element(["https://a.example", "https://b.example"])], set_dtypes=True
    )

    links = frame.explode(["link_urls", "link_texts", "link_start_indexes"])

    assert list(zip(links.link_urls, links.link_texts, links.link_start_indexes)) == [
        ("https://a.example", "alpha", 0),
        ("https://b.example", "beta", 6),
    ]


@pytest.mark.parametrize("set_dtypes", [False, True])
def test_json_records_keep_urls_as_json_arrays(set_dtypes):
    urls = ["https://a.example", "https://b.example"]
    frame = convert_to_dataframe([make_element(urls)], set_dtypes=set_dtypes)

    records = json.loads(frame.to_json(orient="records"))

    assert records[0]["link_urls"] == urls


@pytest.mark.parametrize("set_dtypes", [False, True])
def test_native_huggingface_dataset_keeps_the_link_sequence(set_dtypes):
    datasets = pytest.importorskip("datasets")
    urls = ["https://a.example", "https://b.example"]
    frame = convert_to_dataframe([make_element(urls)], set_dtypes=set_dtypes)

    dataset = datasets.Dataset.from_pandas(frame, preserve_index=False)

    assert dataset[0]["link_urls"] == urls
    assert dataset[0]["link_texts"] == ["alpha", "beta"]


def test_typed_dataframe_does_not_create_a_missing_link_column():
    frame = convert_to_dataframe([Text("no links")], set_dtypes=True)

    assert "link_urls" not in frame.columns
