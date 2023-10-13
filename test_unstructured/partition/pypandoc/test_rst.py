from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.rst import partition_rst


def test_partition_rst_from_filename(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"
    for element in elements:
        assert element.metadata.filename == "README.rst"


def test_partition_rst_from_filename_returns_uns_elements(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    assert isinstance(elements[0], Title)


def test_partition_rst_from_filename_with_metadata_filename(
    filename="example-docs/README.rst",
):
    elements = partition_rst(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_rst_from_file(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f)
    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"
    for element in elements:
        assert element.metadata.filename is None


def test_partition_rst_from_file_with_metadata_filename(
    filename="example-docs/README.rst",
):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f, metadata_filename="test")
    assert elements[0] == Title("Example Docs")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_rst_from_filename_exclude_metadata(
    filename="example-docs/README.rst",
):
    elements = partition_rst(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rst_from_file_exclude_metadata(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rst_metadata_date(
    mocker,
    filename="example-docs/README.rst",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_rst(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_rst_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.rst",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_rst(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_rst_from_file_metadata_date(
    mocker,
    filename="example-docs/README.rst",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_rst(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_rst_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.rst",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_rst(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_rst_with_json():
    elements = partition_rst(example_doc_path("README.rst"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_rst(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    chunk_elements = partition_rst(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_rst_element_metadata_has_languages():
    filename = "example-docs/README.rst"
    elements = partition_rst(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_rst_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.rst"
    elements = partition_rst(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
