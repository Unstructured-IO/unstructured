from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.org import partition_org


def test_partition_org_from_filename():
    elements = partition_org(example_doc_path("README.org"))

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_filename_with_metadata_filename():
    elements = partition_org(example_doc_path("README.org"), metadata_filename="test")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filename == "test"


def test_partition_org_from_file():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_file_with_metadata_filename():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f, metadata_filename="test")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filename == "test"


def test_partition_org_from_filename_exclude_metadata():
    elements = partition_org(example_doc_path("README.org"), include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


def test_partition_org_from_file_exclude_metadata():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_org_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.org.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_org(example_doc_path("README.org"))

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_org_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2020-08-04T06:11:47"
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.org.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_org(
        example_doc_path("README.org"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_org_with_json():
    elements = partition_org(example_doc_path("README.org"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_org():
    file_path = example_doc_path("README.org")
    elements = partition_org(file_path)
    chunk_elements = partition_org(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_org_element_metadata_has_languages():
    elements = partition_org(example_doc_path("README.org"))
    assert elements[0].metadata.languages == ["eng"]


def test_partition_org_respects_detect_language_per_element():
    elements = partition_org(
        example_doc_path("language-docs/eng_spa_mult.org"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
