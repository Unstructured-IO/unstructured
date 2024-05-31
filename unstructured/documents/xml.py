from typing import Any, List, Optional, Union

from lxml import etree
from typing_extensions import Self

from unstructured.documents.base import Document, Page
from unstructured.file_utils.encoding import read_txt_file
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

    def _parse_pages_from_element_tree(self) -> List[Page]:
        raise NotImplementedError

    @property
    def pages(self) -> List[Page]:
        """Gets all elements from pages in sequential order."""
        if self._pages is None:
            self._pages = self._parse_pages_from_element_tree()
        return super().pages

    def _read_xml(self, content: str):
        """Reads in an XML file and converts it to an lxml element tree object."""
        # NOTE(robinson) - without the carriage return at the beginning, you get
        # output that looks like the following when you run partition_pdf
        #   'h   3       a   l   i   g   n   =   "   c   e   n   t   e   r   "   >'
        # The correct output is returned once you add the initial return.
        is_html_parser = isinstance(self.parser, etree.HTMLParser)
        if content and not content.startswith("\n") and is_html_parser:
            content = "\n" + content
        if self.document_tree is None:
            try:
                document_tree = etree.fromstring(content, self.parser)
                if document_tree is None:
                    raise ValueError("document_tree is None")

            # NOTE(robinson) - The following ValueError occurs with unicode strings. In that
            # case, we call back to encoding the string and passing in bytes.
            #     ValueError: Unicode strings with encoding declaration are not supported.
            #     Please use  bytes input or XML fragments without declaration.
            except ValueError:
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
    def from_string(
        cls,
        text: str,
        parser: VALID_PARSERS = None,
        stylesheet: Optional[str] = None,
        **kwargs: Any,
    ) -> Self:
        """Supports reading in an XML file as a raw string rather than as a file."""
        logger.info("Reading document from string ...")
        doc = cls(parser=parser, stylesheet=stylesheet, **kwargs)
        doc._read_xml(text)
        return doc

    @classmethod
    def from_file(
        cls,
        filename: str,
        parser: VALID_PARSERS = None,
        stylesheet: Optional[str] = None,
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> Self:
        _, content = read_txt_file(filename=filename, encoding=encoding)

        return cls.from_string(content, parser=parser, stylesheet=stylesheet, **kwargs)
