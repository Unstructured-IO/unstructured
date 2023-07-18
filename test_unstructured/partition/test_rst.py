from unstructured.documents.elements import Title
from unstructured.documents.html import HTMLTitle
from unstructured.partition.rst import partition_rst


def test_partition_rst_from_filename(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"
    for element in elements:
        assert element.metadata.filename == "README.rst"


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


def test_partition_rst_with_include_element_types(
    filename="example-docs/README.rst",
):
    element_types = [HTMLTitle]
    elements = partition_rst(
        filename=filename,
        include_metadata=False,
        include_element_types=element_types,
    )

    for element in elements:
        assert type(element) in element_types


def test_partition_rst_with_exclude_element_types(
    filename="example-docs/README.rst",
):
    element_types = [HTMLTitle]
    elements = partition_rst(
        filename=filename,
        include_metadata=False,
        exclude_element_types=element_types,
    )

    for element in elements:
        assert type(element) not in element_types


def test_partition_rst_from_file_with_include_element_types(
    filename="example-docs/README.rst",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_rst(
            file=f,
            include_metadata=False,
            include_element_types=element_types,
        )

    for element in elements:
        assert type(element) in element_types


def test_partition_rst_from_file_with_exclude_element_types(
    filename="example-docs/README.rst",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_rst(
            file=f,
            include_metadata=False,
            exclude_element_types=element_types,
        )

    for element in elements:
        assert type(element) not in element_types
