from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.org import partition_org


def test_partition_org_from_filename(filename="example-docs/README.org"):
    elements = partition_org(filename=filename)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_filename_with_metadata_filename(filename="example-docs/README.org"):
    elements = partition_org(filename=filename, metadata_filename="test")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filename == "test"


def test_partition_org_from_file(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition_org(file=f)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_file_with_metadata_filename(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition_org(file=f, metadata_filename="test")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filename == "test"


def test_partition_org_from_filename_exclude_metadata():
    elements = partition_org("example-docs/README.org", include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


def test_partition_org_from_file_exclude_metadata(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition_org(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_org_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.org.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_org("example-docs/README.org")

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_org_prefers_metadata_last_modified(mocker: MockFixture):
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch("unstructured.partition.org.get_last_modified", return_value="2029-07-05T09:24:28")

    elements = partition_org(
        "example-docs/README.org", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_org_with_json():
    elements = partition_org(example_doc_path("README.org"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_org(
    filename="example-docs/README.org",
):
    elements = partition_org(filename=filename)
    chunk_elements = partition_org(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_org_element_metadata_has_languages():
    filename = "example-docs/README.org"
    elements = partition_org(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_org_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.org"
    elements = partition_org(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
