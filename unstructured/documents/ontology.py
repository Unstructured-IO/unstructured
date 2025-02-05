"""
This file contains all classes allowed in the ontology V2.
This Type is used as intermediate representation between HTML
and Unstructured Elements.
All the processing could be done without the intermediate representation,
but it simplifies the process.
It needs to be decide whether we keep it or not.

The classes are represented as pydantic models to mimic Unstructured Elements V1 solutions.
However it results in lots of code that could be strongly simplified.

TODO (Pluto): OntologyElement is the only needed class. It could contains data about
 allowed html tags, css classes and descriptions as metadata.
"""

from __future__ import annotations

import uuid
from copy import copy
from enum import Enum
from typing import List, Optional

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field


class ElementTypeEnum(str, Enum):
    layout = "Layout"
    text = "Text"
    list = "List"
    table = "Table"
    media = "Media"
    code = "Code"
    mathematical = "Mathematical"
    reference = "Reference"
    metadata = "Metadata"
    navigation = "Navigation"
    form = "Form"
    annotation = "Annotation"
    specialized_text = "Specialized Text"
    document_specific = "Document-Specific"


class OntologyElement(BaseModel):
    text: Optional[str] = Field("", description="Text content of the element")
    css_class_name: Optional[str] = Field(
        default_factory=lambda: "", description="CSS class associated with the element"
    )
    html_tag_name: Optional[str] = Field(
        default_factory=lambda: "", description="HTML Tag name associated with the element"
    )
    elementType: ElementTypeEnum = Field(..., description="Type of the element")
    children: List["OntologyElement"] = Field(
        default_factory=list, description="List of child elements"
    )

    description: str = Field(..., description="Description of the element")
    allowed_tags: List[str] = Field(..., description="HTML tags associated with the element")

    additional_attributes: Optional[dict] = Field(
        {}, description="Optional HTML attributes or CSS properties"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.css_class_name == "":  # if None, then do not set
            self.css_class_name = self.__class__.__name__
        if self.html_tag_name == "":
            self.html_tag_name = self.allowed_tags[0]
        if "id" not in self.additional_attributes:
            self.additional_attributes["id"] = self.generate_unique_id()

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4()).replace("-", "")

    def to_html(self, add_children=True) -> str:
        additional_attrs = copy(self.additional_attributes)
        additional_attrs.pop("class", None)

        attr_str = self._construct_attribute_string(additional_attrs)
        class_attr = f'class="{self.css_class_name}"' if self.css_class_name else ""

        combined_attr_str = f"{class_attr} {attr_str}".strip()

        children_html = self._generate_children_html(add_children)

        result_html = self._generate_final_html(combined_attr_str, children_html)

        return result_html

    def to_text(self, add_children=True, add_img_alt_text=True) -> str:
        """
        Returns the text representation of the element.

        Args:
            add_children: If True, the text of the children will be included.
                            Otherwise, element is represented as single self-closing tag.
            add_img_alt_text: If True, the alt text of the image will be included.
        """
        if self.children and add_children:
            children_text = " ".join(
                child.to_text(add_children, add_img_alt_text).strip() for child in self.children
            )
            return children_text

        text = BeautifulSoup(self.to_html(), "html.parser").get_text().strip()

        if add_img_alt_text and self.html_tag_name == "img" and "alt" in self.additional_attributes:
            text += f" {self.additional_attributes.get('alt', '')}"

        return text.strip()

    def _construct_attribute_string(self, attributes: dict) -> str:
        return " ".join(
            f'{key}="{value}"' if value else f"{key}" for key, value in attributes.items()
        )

    def _generate_children_html(self, add_children: bool) -> str:
        if not add_children or not self.children:
            return ""
        return "".join(child.to_html() for child in self.children)

    def _generate_final_html(self, attr_str: str, children_html: str) -> str:
        text = self.text or ""

        if text or children_html:
            inside_tag_text = f"{text} {children_html}".strip()
            return f"<{self.html_tag_name} {attr_str}>{inside_tag_text}</{self.html_tag_name}>"
        else:
            return f"<{self.html_tag_name} {attr_str} />"

    @property
    def id(self) -> str | None:
        return self.additional_attributes.get("id", None)

    @property
    def page_number(self) -> int | None:
        if "data-page-number" in self.additional_attributes:
            try:
                return int(self.additional_attributes.get("data-page-number"))
            except ValueError:
                return None
        return None


def remove_ids_and_class_from_table(soup: Tag):
    for tag in soup.find_all(True):
        if tag.name == "table":
            continue  # We keep table tag
        tag.attrs.pop("class", None)
        tag.attrs.pop("id", None)
    return soup


# Define specific elements
class Document(OntologyElement):
    description: str = Field("Root element of the document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["body"], frozen=True)


class Section(OntologyElement):
    description: str = Field("A distinct part or subdivision of a document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["section"], frozen=True)


class Page(OntologyElement):
    description: str = Field("A single side of a paper in a document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["div"], frozen=True)


class Column(OntologyElement):
    description: str = Field("A vertical section of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["div"], frozen=True)


class Paragraph(OntologyElement):
    description: str = Field("A self-contained unit of discourse in writing", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["p"], frozen=True)


class Header(OntologyElement):
    description: str = Field("The top section of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["header"], frozen=True)


class Footer(OntologyElement):
    description: str = Field("The bottom section of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["footer"], frozen=True)


class Sidebar(OntologyElement):
    description: str = Field("A side section of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["aside"], frozen=True)


class PageBreak(OntologyElement):
    description: str = Field("A break between pages", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.layout, frozen=True)
    allowed_tags: List[str] = Field(["hr"], frozen=True)


class Title(OntologyElement):
    description: str = Field("Main heading of a document or section", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["h1"], frozen=True)


class Subtitle(OntologyElement):
    description: str = Field("Secondary title of a document or section", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["h2"], frozen=True)


class Heading(OntologyElement):
    description: str = Field("Section headings (levels 1-6)", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["h1", "h2", "h3", "h4", "h5", "h6"], frozen=True)


class NarrativeText(OntologyElement):
    description: str = Field("Main content text", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["p"], frozen=True)


class Quote(OntologyElement):
    description: str = Field("A repetition of someone else's statement", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["blockquote"], frozen=True)


class Footnote(OntologyElement):
    description: str = Field("A note at the bottom of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["div"], frozen=True)


class Caption(OntologyElement):
    description: str = Field("Text describing a figure or image", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["figcaption"], frozen=True)


class PageNumber(OntologyElement):
    description: str = Field("The number of a page", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class UncategorizedText(OntologyElement):
    description: str = Field("Miscellaneous text", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.text, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class OrderedList(OntologyElement):
    description: str = Field("A list with a specific sequence", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.list, frozen=True)
    allowed_tags: List[str] = Field(["ol"], frozen=True)


class UnorderedList(OntologyElement):
    description: str = Field("A list without a specific sequence", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.list, frozen=True)
    allowed_tags: List[str] = Field(["ul"], frozen=True)


class DefinitionList(OntologyElement):
    description: str = Field("A list of terms and their definitions", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.list, frozen=True)
    allowed_tags: List[str] = Field(["dl"], frozen=True)


class ListItem(OntologyElement):
    description: str = Field("An item in a list", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.list, frozen=True)
    allowed_tags: List[str] = Field(["li"], frozen=True)


class Table(OntologyElement):
    description: str = Field("A structured set of data", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["table"], frozen=True)

    def to_html(self, add_children=True) -> str:
        soup = BeautifulSoup(super().to_html(add_children), "html.parser")
        soup = remove_ids_and_class_from_table(soup)
        return str(soup)


class TableBody(OntologyElement):
    description: str = Field("A body of the table", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["tbody"], frozen=True)


class TableHeader(OntologyElement):
    description: str = Field("A header of the table", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["thead"], frozen=True)


class TableRow(OntologyElement):
    description: str = Field("A row in a table", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["tr"], frozen=True)


class TableCell(OntologyElement):
    description: str = Field("A cell in a table", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["td"], frozen=True)


# Note(Pluto): Renamed from TableCellHeader to TableHeaderCell to be consistent with TableCell
class TableCellHeader(OntologyElement):
    description: str = Field("A header cell in a table", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["th"], frozen=True)


class Image(OntologyElement):
    description: str = Field("A visual representation", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["img"], frozen=True)


class Figure(OntologyElement):
    description: str = Field("An illustration or diagram in a document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["figure"], frozen=True)


class Video(OntologyElement):
    description: str = Field("A moving visual media element", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["video"], frozen=True)


class Audio(OntologyElement):
    description: str = Field("A sound or music element", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["audio"], frozen=True)


class Barcode(OntologyElement):
    description: str = Field("A machine-readable representation of data", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["img"], frozen=True)


class QRCode(OntologyElement):
    description: str = Field("A two-dimensional barcode", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["img"], frozen=True)


class Logo(OntologyElement):
    description: str = Field("A graphical representation of a company or brand", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.media, frozen=True)
    allowed_tags: List[str] = Field(["img"], frozen=True)


class CodeBlock(OntologyElement):
    description: str = Field("A block of programming code", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.code, frozen=True)
    allowed_tags: List[str] = Field(["pre", "code"], frozen=True)


class InlineCode(OntologyElement):
    description: str = Field("Code within a line of text", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.code, frozen=True)
    allowed_tags: List[str] = Field(["code"], frozen=True)


class Formula(OntologyElement):
    description: str = Field("A mathematical formula", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.mathematical, frozen=True)
    allowed_tags: List[str] = Field(["math"], frozen=True)


class Equation(OntologyElement):
    description: str = Field("A mathematical equation", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.mathematical, frozen=True)
    allowed_tags: List[str] = Field(["math"], frozen=True)


class FootnoteReference(OntologyElement):
    description: str = Field(
        "A subscripted reference to a note at the bottom of a page", frozen=True
    )
    elementType: ElementTypeEnum = Field(ElementTypeEnum.reference, frozen=True)
    allowed_tags: List[str] = Field(["sub"], frozen=True)


class Citation(OntologyElement):
    description: str = Field("A reference to a source", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.reference, frozen=True)
    allowed_tags: List[str] = Field(["cite"], frozen=True)


class Bibliography(OntologyElement):
    description: str = Field("A list of sources", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.reference, frozen=True)
    allowed_tags: List[str] = Field(["ul"], frozen=True)


class Glossary(OntologyElement):
    description: str = Field("A list of terms and their definitions", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.reference, frozen=True)
    allowed_tags: List[str] = Field(["dl"], frozen=True)


class Author(OntologyElement):
    description: str = Field("The creator of the document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.metadata, frozen=True)
    allowed_tags: List[str] = Field(["meta"], frozen=True)


class MetaDate(OntologyElement):
    description: str = Field("The date associated with the document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.metadata, frozen=True)
    allowed_tags: List[str] = Field(["meta"], frozen=True)


class Keywords(OntologyElement):
    description: str = Field("Key terms associated with the document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.metadata, frozen=True)
    allowed_tags: List[str] = Field(["meta"], frozen=True)


class Abstract(OntologyElement):
    description: str = Field("A summary of the document", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.metadata, frozen=True)
    allowed_tags: List[str] = Field(["section"], frozen=True)


class Hyperlink(OntologyElement):
    description: str = Field("A reference to data that can be directly followed", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.navigation, frozen=True)
    allowed_tags: List[str] = Field(["a"], frozen=True)


class TableOfContents(OntologyElement):
    description: str = Field(
        "A list of the document's contents. Total table columns will be "
        "equal to the degree of hierarchy (n) plus 1 for the target value. "
        "Header Row: L1,L2,...Ln,Value",
        frozen=True,
    )
    elementType: ElementTypeEnum = Field(ElementTypeEnum.table, frozen=True)
    allowed_tags: List[str] = Field(["table"], frozen=True)

    def to_html(self, add_children=True) -> str:
        soup = BeautifulSoup(super().to_html(add_children), "html.parser")
        soup = remove_ids_and_class_from_table(soup)
        return str(soup)


class Index(OntologyElement):
    description: str = Field("An alphabetical list of terms and their page numbers", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.navigation, frozen=True)
    allowed_tags: List[str] = Field(["nav"], frozen=True)


class Form(OntologyElement):
    description: str = Field("A document section with interactive controls", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["form"], frozen=True)


class FormField(OntologyElement):
    description: str = Field("A property value of a form", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["label"], frozen=True)


class FormFieldValue(OntologyElement):
    description: str = Field("A field for user input", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["input"], frozen=True)

    def to_text(self, add_children=True, add_img_alt_text=True) -> str:
        text = super().to_text(add_children, add_img_alt_text)
        value = self.additional_attributes.get("value", "")
        if not value:
            return text
        return f"{text} {value}".strip()


class Checkbox(OntologyElement):
    description: str = Field("A small box that can be checked or unchecked", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["input"], frozen=True)


class RadioButton(OntologyElement):
    description: str = Field("A circular button that can be selected", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["input"], frozen=True)


class Button(OntologyElement):
    description: str = Field("An interactive button element", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.form, frozen=True)
    allowed_tags: List[str] = Field(["button"], frozen=True)


class Comment(OntologyElement):
    description: str = Field("A note or remark", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.annotation, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class Highlight(OntologyElement):
    description: str = Field("Emphasized text or section", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.annotation, frozen=True)
    allowed_tags: List[str] = Field(["mark"], frozen=True)


class RevisionInsertion(OntologyElement):
    description: str = Field("A changed or edited element", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.annotation, frozen=True)
    allowed_tags: List[str] = Field(["ins"], frozen=True)


class RevisionDeletion(OntologyElement):
    description: str = Field("A changed or edited element", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.annotation, frozen=True)
    allowed_tags: List[str] = Field(["del"], frozen=True)


class Address(OntologyElement):
    description: str = Field("A physical location", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["address"], frozen=True)


class EmailAddress(OntologyElement):
    description: str = Field("An email address", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["a"], frozen=True)


class PhoneNumber(OntologyElement):
    description: str = Field("A telephone number", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class CalendarDate(OntologyElement):
    description: str = Field("A calendar date", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["time"], frozen=True)


class Time(OntologyElement):
    description: str = Field("A specific time", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["time"], frozen=True)


class Currency(OntologyElement):
    description: str = Field("A monetary value", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class Measurement(OntologyElement):
    description: str = Field("A quantitative value with units", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.specialized_text, frozen=True)
    allowed_tags: List[str] = Field(["span"], frozen=True)


class Letterhead(OntologyElement):
    description: str = Field("The heading at the top of a letter", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.document_specific, frozen=True)
    allowed_tags: List[str] = Field(["header"], frozen=True)


class Signature(OntologyElement):
    description: str = Field("A person's name written in a distinctive way", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.document_specific, frozen=True)
    allowed_tags: List[str] = Field(["img", "svg"], frozen=True)


class Watermark(OntologyElement):
    description: str = Field("A faint design made in paper during manufacture", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.document_specific, frozen=True)
    allowed_tags: List[str] = Field(["div"], frozen=True)


class Stamp(OntologyElement):
    description: str = Field("An official mark or seal", frozen=True)
    elementType: ElementTypeEnum = Field(ElementTypeEnum.document_specific, frozen=True)
    allowed_tags: List[str] = Field(["img", "svg"], frozen=True)
