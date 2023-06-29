from unstructured.documents.elements import Title
from unstructured.partition.rst import partition_rst


def test_partition_rst_from_filename(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


def test_partition_rst_from_file(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


def test_partition_rst_from_filename_exclude_metadata(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert any(elements[i].metadata.to_dict()) == {}


def test_partition_rst_from_file_exclude_metadata(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert any(elements[i].metadata.to_dict()) == {}
