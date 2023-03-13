from typing import List, Optional, Union

from lxml import etree

from unstructured.documents.base import Document, Page
from unstructured.logger import logger

VALID_PARSERS = Union[etree.HTMLParser, etree.XMLParser, None]


class XMLDocument(Document):
    """Class for handling .xml documents. This class uses rules based parsing to identify
    sections of interest within the document."""

    def __init__(
        self,
        stylesheet: Optional[str] = None,
        parser: VALID_PARSERS = None,
    ):
        """Class for parsing XML documents. XML documents are parsed using lxml.

        Parameters
        ----------
        filename:
            The name of the XML file to read
        stylesheet:
            An XLST stylesheet that can be applied to transform the XML file
        parser:
            The lxml parser to use with the file. The HTML parser is used by default
            because it is more tolerant of special characters and malformed XML. If you
            are using a stylesheet, you likely want the XMLParser.
        """
        if not parser:
            parser = (
                etree.XMLParser(remove_comments=True)
                if stylesheet
                else etree.HTMLParser(remove_comments=True)
            )

        self.stylesheet = stylesheet
        self.parser = parser
        self.document_tree = None
        super().__init__()

    def _read(self):
        raise NotImplementedError

    @property
    def pages(self) -> List[Page]:
        """Gets all elements from pages in sequential order."""
        if self._pages is None:
            self._pages = self._read()
        return super().pages

    def _read_xml(self, content):
        """Reads in an XML file and converts it to an lxml element tree object."""
        if self.document_tree is None:
            document_tree = etree.fromstring(content.encode(), self.parser)

            if self.stylesheet:
                if isinstance(self.parser, etree.HTMLParser):
                    logger.warning(
                        "You are using the HTML parser with an XSLT stylesheet. "
                        "Stylesheets are more commonly parsed with the "
                        "XMLParser. If your HTML does not display properly, try "
                        "`import lxml.etree as etree` and setting "
                        "`parser=etree.XMLParser()` instead.",
                    )
                xslt = etree.parse(self.stylesheet)
                transform = etree.XSLT(xslt)
                document_tree = transform(document_tree)

            self.document_tree = document_tree

        return self.document_tree

    @classmethod
    def from_string(cls, text: str, parser: VALID_PARSERS = None, stylesheet: Optional[str] = None):
        """Supports reading in an XML file as a raw string rather than as a file."""
        logger.info("Reading document from string ...")
        doc = cls(parser=parser, stylesheet=stylesheet)
        doc._read_xml(text)
        return doc

    @classmethod
    def from_file(
        cls,
        filename,
        parser: VALID_PARSERS = None,
        stylesheet: Optional[str] = None,
        encoding: Optional[str] = "utf-8",
    ):
        with open(filename, encoding=encoding) as f:
            content = f.read()
        return cls.from_string(content, parser=parser, stylesheet=stylesheet)
