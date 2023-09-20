import uuid

import pytest
from jsonschema import validate

from unstructured.documents import elements
from unstructured.documents.schema import _element_schema

element_id = uuid.uuid4()
coordinates = ((1.1, 2.2), (3.3, 4.4))
coordinate_system = elements.CoordinateSystem(width=87, height=78)
data_source = elements.DataSourceMetadata(
    url="some_url",
    version="some_version",
    record_locator={"random": "text", "list": [1, 2, 3]},
    date_created="date_created",
    date_modified="date_modified",
    date_processed="date_processed",
)
coordinates_metadata = elements.CoordinatesMetadata(
    points=coordinates,
    system=coordinate_system,
)
metadata = elements.ElementMetadata(
    coordinates=coordinates_metadata,
    data_source=data_source,
    filename="some_filename",
    file_directory="some_file_directory",
    last_modified="some_last_modified",
    filetype="some_filetype",
    attached_to_filename="some_attached_to_filename",
    parent_id=uuid.uuid4(),
    category_depth=234,
    page_number=777,
    page_name="some_page_name",
    url="some_url",
    link_urls=["some", "link", "urls"],
    link_texts=["some", "link", "texts"],
    sent_from=["some", "sent", "from"],
    sent_to=["some", "sent", "to"],
    subject="some_subject",
    section="some_section",
    header_footer_type="some_header_footer_type",
    emphasized_text_contents=["some", "emphasized", "text", "contents"],
    emphasized_text_tags=["some", "emphasized", "text", "tags"],
    text_as_html="<some_html>",
    regex_metadata={
        "some_regex_metadata": [
            elements.RegexMetadata(text="some text", start=3, end=5),
            elements.RegexMetadata(text="some more text", start=33, end=55),
        ],
    },
    detection_class_prob=0.222,
)


def test_checkbox_element():
    element = elements.CheckBox(
        element_id=element_id,
        coordinates=coordinates,
        coordinate_system=coordinate_system,
        checked=True,
        metadata=metadata,
    )

    validate(element.to_dict(), schema=_element_schema)


def test_formula_element():
    element = elements.Formula(
        element_id=element_id,
        coordinates=coordinates,
        coordinate_system=coordinate_system,
        metadata=metadata,
    )

    validate(element.to_dict(), schema=_element_schema)


@pytest.mark.parametrize(
    "element_type",
    [
        elements.Text,
        elements.CompositeElement,
        elements.FigureCaption,
        elements.NarrativeText,
        elements.ListItem,
        elements.Title,
        elements.Address,
        elements.EmailAddress,
        elements.Image,
        elements.PageBreak,
        elements.Table,
        elements.Header,
        elements.Footer,
    ],
)
def test_text_elements(element_type):
    element = element_type(
        text="some_text",
        element_id=element_id,
        coordinates=coordinates,
        coordinate_system=coordinate_system,
        metadata=metadata,
    )

    validate(element.to_dict(), schema=_element_schema)
