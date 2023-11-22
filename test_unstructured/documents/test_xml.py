# pyright: reportPrivateUsage=false

import os
from pathlib import Path

import pytest
from lxml import etree

from unstructured.documents.xml import XMLDocument

FILEPATH = Path(__file__).absolute().parent


@pytest.fixture()
def sample_document():
    return """"<SEC-DOCUMENT>
    <TYPE>10-K
    <COMPANY>Proctor & Gamble
</SEC-DOCUMENT>"""


def test_read_xml(sample_document, tmpdir):
    filename = os.path.join(tmpdir.dirname, "sample-document.xml")
    with open(filename, "w") as f:
        f.write(sample_document)

    xml_document = XMLDocument.from_file(filename=filename)
    document_tree = xml_document.document_tree
    type_tag = document_tree.find(".//type")
    assert type_tag.text.strip() == "10-K"

    # Test to make sure the & character is retained
    company_tag = document_tree.find(".//company")
    assert company_tag.text.strip() == "Proctor & Gamble"


def test_xml_read_raises():
    xml_document = XMLDocument()
    with pytest.raises(NotImplementedError):
        xml_document._parse_pages_from_element_tree()


def test_from_string(sample_document):
    xml_document = XMLDocument.from_string(sample_document)
    type_tag = xml_document.document_tree.find(".//type")
    assert type_tag.text.strip() == "10-K"


def test_from_string_with_pre_tag():
    sample_document = """
    <pre>
    <SEC-DOCUMENT>
    <TYPE>10-K
    <COMPANY>Proctor & Gamble
    </SEC-DOCUMENT>
    </pre>
    """
    xml_document = XMLDocument.from_string(sample_document)
    type_tag = xml_document.document_tree.find(".//type")
    assert type_tag.text.strip() == "10-K"


def test_read_with_stylesheet():
    filename = os.path.join(FILEPATH, "..", "..", "example-docs", "factbook.xml")
    stylesheet = os.path.join(FILEPATH, "..", "..", "example-docs", "unsupported", "factbook.xsl")

    xml_document = XMLDocument.from_file(filename=filename, stylesheet=stylesheet)
    doc_tree = xml_document.document_tree
    # NOTE(robinson) - The table heading row plus one row for each of the four data items
    assert int(doc_tree.xpath("count(//tr)")) == 5
    # NOTE(robinson) - Four data elements x four attributes for each
    assert int(doc_tree.xpath("count(//td)")) == 16


def test_read_with_stylesheet_warns_with_html_parser(caplog):
    filename = os.path.join(FILEPATH, "..", "..", "example-docs", "factbook.xml")
    stylesheet = os.path.join(FILEPATH, "..", "..", "example-docs", "unsupported", "factbook.xsl")

    XMLDocument.from_file(filename=filename, stylesheet=stylesheet, parser=etree.HTMLParser())
    assert "WARNING" in caplog.text
