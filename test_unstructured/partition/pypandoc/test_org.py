from tempfile import SpooledTemporaryFile

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


def test_partition_org_from_filename_exclude_metadata(filename="example-docs/README.org"):
    elements = partition_org(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_org_from_file_exclude_metadata(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition_org(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_org_metadata_date(
    mocker,
    filename="example-docs/README.org",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_org(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_org_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.org",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_org(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_org_from_file_metadata_date(
    mocker,
    filename="example-docs/README.org",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_org(
            file=f,
        )

    assert elements[0].metadata.last_modified is None


def test_partition_org_from_file_explicit_get_metadata_date(
    mocker,
    filename="example-docs/README.org",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_org(file=f, date_from_file_object=True)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_org_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.org",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_org(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_org_from_file_without_metadata_date(
    filename="example-docs/README.org",
):
    """Test partition_org() with file that are not possible to get last modified date"""

    with open(filename, "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_org(file=sf, date_from_file_object=True)

    assert elements[0].metadata.last_modified is None


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
