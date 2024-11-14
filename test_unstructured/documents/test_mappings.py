from collections import defaultdict
from typing import Dict, Type

from unstructured.documents import elements, ontology
from unstructured.documents.mappings import (
    ALL_ONTOLOGY_ELEMENT_TYPES,
    HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP,
    ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE,
    get_all_subclasses,
)
from unstructured.documents.ontology import OntologyElement


def _get_exclusive_html_tags() -> dict[str, Type[OntologyElement]]:
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


def test_if_all_exclusive_html_tags_are_mapped_to_ontology_elements():
    exclusive_html_tags = _get_exclusive_html_tags()
    for expected_tag, expected_element_type in exclusive_html_tags.items():
        assert expected_tag in HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP
        assert HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP[expected_tag] == expected_element_type


def test_all_expected_ontology_types_are_subclasses_of_OntologyElement():
    for element_type in HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP.values():
        assert issubclass(element_type, OntologyElement)


def test_ontology_to_unstructured_mapping_has_valid_types():
    for (
        ontology_element,
        unstructured_element,
    ) in ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE.items():
        assert issubclass(unstructured_element, elements.Element)
        assert issubclass(ontology_element, ontology.OntologyElement)


def test_all_ontology_elements_are_defined_in_mapping_to_unstructured():
    for ontology_element in get_all_subclasses(ontology.OntologyElement):
        assert ontology_element in ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE
