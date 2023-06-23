from unstructured.documents.elements import Title
from unstructured.partition.org import partition_org


def test_partition_org_from_filename(filename="example-docs/README.org"):
    elements = partition_org(filename=filename)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_file(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition_org(file=f)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"
