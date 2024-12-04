"""
This module contains mapping between:
HTML Tags <-> Elements Ontology <-> Unstructured Element classes
They are used to simplify transformations between different representations
of parsed documents
"""

from typing import Any, Dict, Type

from unstructured.documents import elements, ontology
from unstructured.documents.elements import Element


def get_all_subclasses(cls) -> list[Any]:
    """
    Recursively find all subclasses of a given class.

    Parameters:
    cls (type): The class for which to find all subclasses.

    Returns:
    list: A list of all subclasses of the given class.
    """
    subclasses = cls.__subclasses__()
    all_subclasses = subclasses.copy()

    for subclass in subclasses:
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses


def get_ontology_to_unstructured_type_mapping() -> dict[str, Element]:
    """
    Get a mapping of ontology element to unstructured type.

    The dictionary here was created base on ontology mapping json
    Can be generated via the following code:
    ```
        ontology_elements_list = json.loads(
            Path("unstructured_element_ontology.json").read_text()
        )
        ontology_to_unstructured_class_mapping = {
            ontology_element["name"]: ontology_element["ontologyV1Mapping"]
            for ontology_element in ontology_elements_list
    }
    ```

    Returns:
    dict: A dictionary where keys are ontology element classes
          and values are unstructured types.
    """
    ontology_to_unstructured_class_mapping = {
        ontology.Document: elements.Text,
        ontology.Section: elements.Text,
        ontology.Page: elements.Text,
        ontology.Column: elements.Text,
        ontology.Paragraph: elements.NarrativeText,
        ontology.Header: elements.Header,
        ontology.Footer: elements.Footer,
        ontology.Sidebar: elements.Text,
        ontology.PageBreak: elements.PageBreak,
        ontology.Title: elements.Title,
        ontology.Subtitle: elements.Title,
        ontology.Heading: elements.Title,
        ontology.NarrativeText: elements.NarrativeText,
        ontology.Quote: elements.NarrativeText,
        ontology.Footnote: elements.Text,
        ontology.Caption: elements.FigureCaption,
        ontology.PageNumber: elements.PageNumber,
        ontology.UncategorizedText: elements.Text,
        ontology.OrderedList: elements.Text,
        ontology.UnorderedList: elements.Text,
        ontology.DefinitionList: elements.Text,
        ontology.ListItem: elements.ListItem,
        ontology.Table: elements.Table,
        ontology.TableRow: elements.Table,
        ontology.TableCell: elements.Table,
        ontology.TableCellHeader: elements.Table,
        ontology.TableBody: elements.Table,
        ontology.TableHeader: elements.Table,
        ontology.Image: elements.Image,
        ontology.Figure: elements.Image,
        ontology.Video: elements.Text,
        ontology.Audio: elements.Text,
        ontology.Barcode: elements.Image,
        ontology.QRCode: elements.Image,
        ontology.Logo: elements.Image,
        ontology.CodeBlock: elements.CodeSnippet,
        ontology.InlineCode: elements.CodeSnippet,
        ontology.Formula: elements.Formula,
        ontology.Equation: elements.Formula,
        ontology.FootnoteReference: elements.Text,
        ontology.Citation: elements.Text,
        ontology.Bibliography: elements.Text,
        ontology.Glossary: elements.Text,
        ontology.Author: elements.Text,
        ontology.MetaDate: elements.Text,
        ontology.Keywords: elements.Text,
        ontology.Abstract: elements.NarrativeText,
        ontology.Hyperlink: elements.Text,
        ontology.TableOfContents: elements.Table,
        ontology.Index: elements.Text,
        ontology.Form: elements.Text,
        ontology.FormField: elements.Text,
        ontology.FormFieldValue: elements.Text,
        ontology.Checkbox: elements.Text,
        ontology.RadioButton: elements.Text,
        ontology.Button: elements.Text,
        ontology.Comment: elements.Text,
        ontology.Highlight: elements.Text,
        ontology.RevisionInsertion: elements.Text,
        ontology.RevisionDeletion: elements.Text,
        ontology.Address: elements.Address,
        ontology.EmailAddress: elements.EmailAddress,
        ontology.PhoneNumber: elements.Text,
        ontology.CalendarDate: elements.Text,
        ontology.Time: elements.Text,
        ontology.Currency: elements.Text,
        ontology.Measurement: elements.Text,
        ontology.Letterhead: elements.Header,
        ontology.Signature: elements.Text,
        ontology.Watermark: elements.Text,
        ontology.Stamp: elements.Text,
    }

    return ontology_to_unstructured_class_mapping


ALL_ONTOLOGY_ELEMENT_TYPES = get_all_subclasses(ontology.OntologyElement)
HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP: Dict[tuple[str, str], Type[ontology.OntologyElement]] = {
    (tag, element_type().css_class_name): element_type
    for element_type in ALL_ONTOLOGY_ELEMENT_TYPES
    for tag in element_type().allowed_tags
}
CSS_CLASS_TO_ELEMENT_TYPE_MAP: Dict[str, Type[ontology.OntologyElement]] = {
    element_type().css_class_name: element_type
    for element_type in ALL_ONTOLOGY_ELEMENT_TYPES
    for tag in element_type().allowed_tags
}

HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP: Dict[str, Type[ontology.OntologyElement]] = {
    "a": ontology.Hyperlink,
    "address": ontology.Address,
    "aside": ontology.Sidebar,
    "audio": ontology.Audio,
    "blockquote": ontology.Quote,
    "body": ontology.Document,
    "button": ontology.Button,
    "cite": ontology.Citation,
    "code": ontology.CodeBlock,
    "del": ontology.RevisionDeletion,
    "div": ontology.UncategorizedText,
    "dl": ontology.DefinitionList,
    "figcaption": ontology.Caption,
    "figure": ontology.Figure,
    "footer": ontology.Footer,
    "form": ontology.Form,
    "h1": ontology.Title,
    "h2": ontology.Subtitle,
    "h3": ontology.Heading,
    "h4": ontology.Heading,
    "h5": ontology.Heading,
    "h6": ontology.Heading,
    "header": ontology.Header,
    "hr": ontology.PageBreak,
    "img": ontology.Image,
    "input": ontology.Checkbox,
    "ins": ontology.RevisionInsertion,
    "label": ontology.FormField,
    "li": ontology.ListItem,
    "mark": ontology.Highlight,
    "math": ontology.Equation,
    "meta": ontology.Keywords,
    "nav": ontology.Index,
    "ol": ontology.OrderedList,
    "p": ontology.Paragraph,
    "pre": ontology.CodeBlock,
    "section": ontology.Section,
    "span": ontology.UncategorizedText,
    "sub": ontology.FootnoteReference,
    "svg": ontology.Signature,
    "table": ontology.Table,
    "tbody": ontology.TableBody,
    "td": ontology.TableCell,
    "th": ontology.TableCellHeader,
    "thead": ontology.TableHeader,
    "time": ontology.Time,
    "tr": ontology.TableRow,
    "ul": ontology.UnorderedList,
    "video": ontology.Video,
}


ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE = get_ontology_to_unstructured_type_mapping()
