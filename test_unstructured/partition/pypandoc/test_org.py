from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.json import partition_json
from unstructured.partition.org import partition_org
from unstructured.staging.base import elements_to_json


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


def test_partition_org_with_json(filename="example-docs/README.org"):
    elements = partition_org(filename=filename)
    test_elements = partition_json(text=elements_to_json(elements))

    assert elements[0] == test_elements[0]
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_add_chunking_strategy_on_partition_org(
    filename="example-docs/README.org",
):
    elements = partition_org(filename=filename)
    chunk_elements = partition_org(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks
