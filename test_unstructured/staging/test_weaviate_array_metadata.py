"""Generated Weaviate property types must match the arrays in staged metadata."""

from copy import deepcopy

import pytest

from unstructured.documents.elements import ElementMetadata, Text
from unstructured.staging.weaviate import (
    _annotation_to_weaviate_data_type,
    create_unstructured_weaviate_class,
    stage_for_weaviate,
)


@pytest.mark.parametrize(
    ("field", "values", "data_type"),
    [
        ("languages", ["eng", "spa"], "text[]"),
        ("link_urls", ["https://a.example", "https://b.example"], "text[]"),
        ("link_texts", ["alpha", "beta"], "text[]"),
        ("link_start_indexes", [0, 6], "int[]"),
        ("emphasized_text_contents", ["alpha", "beta"], "text[]"),
        ("emphasized_text_tags", ["strong", "em"], "text[]"),
        ("bcc_recipient", ["a@example.com", "b@example.com"], "text[]"),
        ("cc_recipient", ["a@example.com", "b@example.com"], "text[]"),
        ("sent_from", ["a@example.com"], "text[]"),
        ("sent_to", ["a@example.com", "b@example.com"], "text[]"),
    ],
)
def test_schema_declares_the_primitive_arrays_produced_by_staging(field, values, data_type):
    element = Text("alpha beta", metadata=ElementMetadata(**{field: values}))
    before = deepcopy(element.metadata.to_dict())

    schema = create_unstructured_weaviate_class()
    data = stage_for_weaviate([element])

    property_types = {prop["name"]: prop["dataType"] for prop in schema["properties"]}
    assert property_types[field] == [data_type]
    assert data[0][field] == values
    assert element.metadata.to_dict() == before


@pytest.mark.parametrize(
    ("field", "value", "data_type"),
    [
        ("filename", "document.pdf", "text"),
        ("page_number", 2, "int"),
        ("routing_score", 0.5, "number"),
    ],
)
def test_scalar_metadata_keeps_its_existing_property_type(field, value, data_type):
    schema = create_unstructured_weaviate_class()
    data = stage_for_weaviate([Text("sample", metadata=ElementMetadata(**{field: value}))])

    property_types = {prop["name"]: prop["dataType"] for prop in schema["properties"]}
    assert property_types[field] == [data_type]
    assert data[0][field] == value


@pytest.mark.parametrize("wrapper", ["list[{}]", "Optional[list[{}]]", "Optional[List[{}]]"])
@pytest.mark.parametrize(
    ("value_type", "data_type"), [("str", "text[]"), ("int", "int[]"), ("float", "number[]")]
)
def test_primitive_list_annotations_retain_their_container_type(wrapper, value_type, data_type):
    assert _annotation_to_weaviate_data_type(wrapper.format(value_type)) == [data_type]
