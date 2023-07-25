from unstructured.documents.elements import Title
from unstructured.documents.html import HTMLTitle
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


def test_partition_org_with_include_element_types(
    filename="example-docs/README.org",
):
    element_types = [HTMLTitle]
    elements = partition_org(
        filename=filename,
        include_metadata=False,
        include_element_types=element_types,
    )

    for element in elements:
        assert type(element) in element_types


def test_partition_org_with_exclude_element_types(
    filename="example-docs/README.org",
):
    element_types = [HTMLTitle]
    elements = partition_org(
        filename=filename,
        include_metadata=False,
        exclude_element_types=element_types,
    )

    for element in elements:
        assert type(element) not in element_types


def test_partition_org_from_file_with_include_element_types(
    filename="example-docs/README.org",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_org(
            file=f,
            include_metadata=False,
            include_element_types=element_types,
        )

    for element in elements:
        assert type(element) in element_types


def test_partition_org_from_file_with_exclude_element_types(
    filename="example-docs/README.org",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_org(
            file=f,
            include_metadata=False,
            exclude_element_types=element_types,
        )

    for element in elements:
        assert type(element) not in element_types
