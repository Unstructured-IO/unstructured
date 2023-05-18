from unstructured.partition.xml import partition_xml


def test_partition_xml_from_filename(filename="example-docs/factbook.xml"):
    elements = partition_xml(filename=filename, xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "factbook.xml"


def test_partition_xml_from_file(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=filename)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "factbook.xml"


def test_partition_xml_from_filename_with_tags(filename="example-docs/factbook.xml"):
    elements = partition_xml(filename=filename, xml_keep_tags=True)

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == "factbook.xml"


def test_partition_xml_from_file_with_tags(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=filename)

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == "factbook.xml"
