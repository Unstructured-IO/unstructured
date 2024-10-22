"""
This module contains mapping between:
HTML Tags <-> Elements Ontology <-> Unstructured Element classes
They are used to simplify transformations between different representations
of parsed documents
"""

from collections import defaultdict
from typing import Any, Dict, Type

from unstructured.documents.ontology import OntologyElement


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


def get_exclusive_html_tags() -> dict[str, Type[OntologyElement]]:
    """
    Get a mapping of HTML tags to their exclusive OntologyElement types.
    """
    html_tag_to_element_type_mappings: Dict[str, list[Type[OntologyElement]]] = defaultdict(list)
    for element_type in ALL_ONTOLOGY_ELEMENT_TYPES:
        for tag in element_type().allowed_tags:
            html_tag_to_element_type_mappings[tag].append(element_type)

    return {
        tag: element_types[0]
        for tag, element_types in html_tag_to_element_type_mappings.items()
        if len(element_types) == 1
    }


def get_ontology_to_unstructured_type_mapping() -> dict[str, str]:
    """
    Get a mapping of ontology element names to unstructured type names.

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
    dict: A dictionary where keys are ontology element class names
          and values are unstructured type names.
    """
    ontology_to_unstructured_class_mapping = {
        "Document": "UncategorizedText",
        "Section": "UncategorizedText",
        "Page": "UncategorizedText",
        "Column": "UncategorizedText",
        "Paragraph": "NarrativeText",
        "Header": "Header",
        "Footer": "Footer",
        "Sidebar": "UncategorizedText",
        "PageBreak": "PageBreak",
        "Title": "Title",
        "Subtitle": "Title",
        "Heading": "Title",
        "NarrativeText": "NarrativeText",
        "Quote": "NarrativeText",
        "Footnote": "UncategorizedText",
        "Caption": "FigureCaption",
        "PageNumber": "PageNumber",
        "UncategorizedText": "UncategorizedText",
        "OrderedList": "UncategorizedText",
        "UnorderedList": "UncategorizedText",
        "DefinitionList": "UncategorizedText",
        "ListItem": "ListItem",
        "Table": "Table",
        "TableRow": "Table",
        "TableCell": "Table",
        "TableCellHeader": "Table",
        "TableBody": "Table",
        "TableHeader": "Table",
        "Image": "Image",
        "Figure": "Image",
        "Video": "UncategorizedText",
        "Audio": "UncategorizedText",
        "Barcode": "Image",
        "QRCode": "Image",
        "Logo": "Image",
        "CodeBlock": "CodeSnippet",
        "InlineCode": "CodeSnippet",
        "Formula": "Formula",
        "Equation": "Formula",
        "FootnoteReference": "UncategorizedText",
        "Citation": "UncategorizedText",
        "Bibliography": "UncategorizedText",
        "Glossary": "UncategorizedText",
        "Author": "UncategorizedText",
        "MetaDate": "UncategorizedText",
        "Keywords": "UncategorizedText",
        "Abstract": "NarrativeText",
        "Hyperlink": "UncategorizedText",
        "TableOfContents": "UncategorizedText",
        "Index": "UncategorizedText",
        "Form": "UncategorizedText",
        "FormField": "UncategorizedText",
        "FormFieldValue": "UncategorizedText",
        "Checkbox": "UncategorizedText",
        "RadioButton": "UncategorizedText",
        "Button": "UncategorizedText",
        "Comment": "UncategorizedText",
        "Highlight": "UncategorizedText",
        "RevisionInsertion": "UncategorizedText",
        "RevisionDeletion": "UncategorizedText",
        "Address": "Address",
        "EmailAddress": "EmailAddress",
        "PhoneNumber": "UncategorizedText",
        "CalendarDate": "UncategorizedText",
        "Time": "UncategorizedText",
        "Currency": "UncategorizedText",
        "Measurement": "UncategorizedText",
        "Letterhead": "Header",
        "Signature": "UncategorizedText",
        "Watermark": "UncategorizedText",
        "Stamp": "UncategorizedText",
    }

    return ontology_to_unstructured_class_mapping


ALL_ONTOLOGY_ELEMENT_TYPES = get_all_subclasses(OntologyElement)
HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP: Dict[tuple[str, str], Type[OntologyElement]] = {
    (tag, element_type().css_class_name): element_type
    for element_type in ALL_ONTOLOGY_ELEMENT_TYPES
    for tag in element_type().allowed_tags
}
CSS_CLASS_TO_ELEMENT_TYPE_MAP: Dict[str, Type[OntologyElement]] = {
    element_type().css_class_name: element_type
    for element_type in ALL_ONTOLOGY_ELEMENT_TYPES
    for tag in element_type().allowed_tags
}

EXCLUSIVE_HTML_TAG_TO_ELEMENT_TYPE_MAP: Dict[str, Type[OntologyElement]] = get_exclusive_html_tags()
ONTOLOGY_CLASS_NAME_TO_UNSTRUCTURED_ELEMENT_TYPE_NAME = get_ontology_to_unstructured_type_mapping()
