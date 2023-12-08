from dataclasses import dataclass
from unittest import mock

import pytest
from PIL import Image
from unstructured_inference.inference import layout
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layout import DocumentLayout, LayoutElement, PageLayout

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CheckBox,
    CoordinatesMetadata,
    ElementMetadata,
    ElementType,
    FigureCaption,
    Header,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.documents.elements import (
    Image as ImageElement,
)
from unstructured.partition import common
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_DONT, SORT_MODE_XY_CUT


class MockPageLayout(layout.PageLayout):
    def __init__(self, number: int, image: Image):
        self.number = number
        self.image = image

    @property
    def elements(self):
        return [
            LayoutElement(
                type="Headline",
                text="Charlie Brown and the Great Pumpkin",
                bbox=None,
            ),
            LayoutElement(
                type="Subheadline",
                text="The Beginning",
                bbox=None,
            ),
            LayoutElement(
                type="Text",
                text="This time Charlie Brown had it really tricky...",
                bbox=None,
            ),
            LayoutElement(
                type="Title",
                text="Another book title in the same page",
                bbox=None,
            ),
        ]


class MockDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockPageLayout(number=1, image=Image.new("1", (1, 1))),
        ]


def test_normalize_layout_element_dict():
    layout_element = {
        "type": "Title",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "coordinate_system": None,
        "text": "Some lovely text",
    }
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == Title(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_dict_caption():
    layout_element = {
        "type": "Figure",
        "coordinates": ((1, 2), (3, 4), (5, 6), (7, 8)),
        "text": "Some lovely text",
    }
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == ImageElement(
        text="Some lovely text",
        coordinates=((1, 2), (3, 4), (5, 6), (7, 8)),
        coordinate_system=coordinate_system,
    )


@pytest.mark.parametrize(
    ("element_type", "expected_type", "expected_depth"),
    [
        ("Title", Title, None),
        ("Headline", Title, 1),
        ("Subheadline", Title, 2),
        ("Header", Header, None),
    ],
)
def test_normalize_layout_element_headline(element_type, expected_type, expected_depth):
    layout_element = {
        "type": element_type,
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(layout_element, coordinate_system=coordinate_system)
    assert element.metadata.category_depth == expected_depth
    assert isinstance(element, expected_type)


def test_normalize_layout_element_dict_figure_caption():
    layout_element = {
        "type": "FigureCaption",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == FigureCaption(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_dict_misc():
    layout_element = {
        "type": "Misc",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == Text(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_layout_element():
    layout_element = LayoutElement.from_coords(
        type="Text",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="Some lovely text",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == NarrativeText(
        text="Some lovely text",
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_layout_element_narrative_text():
    layout_element = LayoutElement.from_coords(
        type="NarrativeText",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="Some lovely text",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == NarrativeText(
        text="Some lovely text",
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_checked_box():
    layout_element = LayoutElement.from_coords(
        type="Checked",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == CheckBox(
        checked=True,
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_unchecked_box():
    layout_element = LayoutElement.from_coords(
        type="Unchecked",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    element = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert element == CheckBox(
        checked=False,
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
        coordinate_system=coordinate_system,
    )


def test_normalize_layout_element_enumerated_list():
    layout_element = LayoutElement.from_coords(
        type="List",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="1. I'm so cool! 2. You're cool too. 3. We're all cool!",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    elements = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert elements == [
        ListItem(
            text="I'm so cool!",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
        ListItem(
            text="You're cool too.",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
        ListItem(
            text="We're all cool!",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
    ]


def test_normalize_layout_element_bulleted_list():
    layout_element = LayoutElement.from_coords(
        type="List",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="* I'm so cool! * You're cool too. * We're all cool!",
    )
    coordinate_system = PixelSpace(width=10, height=20)
    elements = common.normalize_layout_element(
        layout_element,
        coordinate_system=coordinate_system,
    )
    assert elements == [
        ListItem(
            text="I'm so cool!",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
        ListItem(
            text="You're cool too.",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
        ListItem(
            text="We're all cool!",
            coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
            coordinate_system=coordinate_system,
        ),
    ]


class MockPopenWithError:
    def __init__(self, *args, **kwargs):
        pass

    def communicate(self):
        return b"", b"an error occurred"


def test_convert_office_doc_captures_errors(monkeypatch, caplog):
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", MockPopenWithError)
    common.convert_office_doc("no-real.docx", "fake-directory", target_format="docx")
    assert "an error occurred" in caplog.text


class MockDocxEmptyTable:
    def __init__(self):
        self.rows = []


def test_convert_ms_office_table_to_text_works_with_empty_tables():
    table = MockDocxEmptyTable()
    assert common.convert_ms_office_table_to_text(table, as_html=True) == ""
    assert common.convert_ms_office_table_to_text(table, as_html=False) == ""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<table><tbody><tr><td>👨\\U+1F3FB🔧</td></tr></tbody></table>", True),
        ("<table><tbody><tr><td>Hello!</td></tr></tbody></table>", False),
    ],
)
def test_contains_emoji(text, expected):
    assert common.contains_emoji(text) is expected


def test_document_to_element_list_omits_coord_system_when_coord_points_absent():
    layout_elem_absent_coordinates = MockDocumentLayout()
    for page in layout_elem_absent_coordinates.pages:
        for el in page.elements:
            el.bbox = None
    elements = common.document_to_element_list(layout_elem_absent_coordinates)
    assert elements[0].metadata.coordinates is None


def test_get_page_image_metadata_and_coordinate_system():
    doc = MockDocumentLayout()
    metadata = common._get_page_image_metadata(doc.pages[0])
    assert isinstance(metadata, dict)


def test_set_element_hierarchy():
    elements_to_set = [
        Title(text="Title"),  # 0
        NarrativeText(text="NarrativeText"),  # 1
        FigureCaption(text="FigureCaption"),  # 2
        ListItem(text="ListItem"),  # 3
        ListItem(text="ListItem", metadata=ElementMetadata(category_depth=1)),  # 4
        ListItem(text="ListItem", metadata=ElementMetadata(category_depth=1)),  # 5
        ListItem(text="ListItem"),  # 6
        CheckBox(element_id="some-id-1", checked=True),  # 7
        Title(text="Title 2"),  # 8
        ListItem(text="ListItem"),  # 9
        ListItem(text="ListItem"),  # 10
        Text(text="Text"),  # 11
    ]
    elements = common.set_element_hierarchy(elements_to_set)

    assert (
        elements[1].metadata.parent_id == elements[0].id
    ), "NarrativeText should be child of Title"
    assert (
        elements[2].metadata.parent_id == elements[0].id
    ), "FigureCaption should be child of Title"
    assert elements[3].metadata.parent_id == elements[0].id, "ListItem should be child of Title"
    assert elements[4].metadata.parent_id == elements[3].id, "ListItem should be child of Title"
    assert elements[5].metadata.parent_id == elements[3].id, "ListItem should be child of Title"
    assert elements[6].metadata.parent_id == elements[0].id, "ListItem should be child of Title"
    assert (
        elements[7].metadata.parent_id is None
    ), "CheckBox should be None, as it's not a Text based element"
    assert elements[8].metadata.parent_id is None, "Title 2 should be child of None"
    assert elements[9].metadata.parent_id == elements[8].id, "ListItem should be child of Title 2"
    assert elements[10].metadata.parent_id == elements[8].id, "ListItem should be child of Title 2"
    assert elements[11].metadata.parent_id == elements[8].id, "Text should be child of Title 2"


def test_set_element_hierarchy_custom_rule_set():
    elements_to_set = [
        Header(text="Header"),  # 0
        Title(text="Title"),  # 1
        NarrativeText(text="NarrativeText"),  # 2
        Text(text="Text"),  # 3
        Title(text="Title 2"),  # 4
        FigureCaption(text="FigureCaption"),  # 5
    ]

    custom_rule_set = {
        "Header": ["Title", "Text"],
        "Title": ["NarrativeText", "UncategorizedText", "FigureCaption"],
    }

    elements = common.set_element_hierarchy(
        elements=elements_to_set,
        ruleset=custom_rule_set,
    )

    assert elements[1].metadata.parent_id == elements[0].id, "Title should be child of Header"
    assert (
        elements[2].metadata.parent_id == elements[1].id
    ), "NarrativeText should be child of Title"
    assert elements[3].metadata.parent_id == elements[1].id, "Text should be child of Title"
    assert elements[4].metadata.parent_id == elements[0].id, "Title 2 should be child of Header"
    assert (
        elements[5].metadata.parent_id == elements[4].id
    ), "FigureCaption should be child of Title 2"


@dataclass
class MockImage:
    width = 640
    height = 480
    format = "JPG"


def test_document_to_element_list_handles_parent():
    block1 = LayoutElement.from_coords(1, 2, 3, 4, text="block 1", type="NarrativeText")
    block2 = LayoutElement.from_coords(
        1,
        2,
        3,
        4,
        text="block 2",
        parent=block1,
        type="NarrativeText",
    )
    page = PageLayout(
        number=1,
        image=MockImage(),
    )
    page.elements = [block1, block2]
    doc = DocumentLayout.from_pages([page])
    el1, el2 = common.document_to_element_list(doc)
    assert el2.metadata.parent_id == el1.id


@pytest.mark.parametrize(
    ("sort_mode", "call_count"),
    [(SORT_MODE_DONT, 0), (SORT_MODE_BASIC, 1), (SORT_MODE_XY_CUT, 1)],
)
def test_document_to_element_list_doesnt_sort_on_sort_method(sort_mode, call_count):
    block1 = LayoutElement.from_coords(1, 2, 3, 4, text="block 1", type="NarrativeText")
    block2 = LayoutElement.from_coords(
        1,
        2,
        3,
        4,
        text="block 2",
        parent=block1,
        type="NarrativeText",
    )
    page = PageLayout(
        number=1,
        image=MockImage(),
    )
    page.elements = [block1, block2]
    doc = DocumentLayout.from_pages([page])
    with mock.patch.object(common, "sort_page_elements") as mock_sort_page_elements:
        common.document_to_element_list(doc, sortable=True, sort_mode=sort_mode)
    assert mock_sort_page_elements.call_count == call_count


def test_document_to_element_list_sets_category_depth_titles():
    layout_with_hierarchies = MockDocumentLayout()
    elements = common.document_to_element_list(layout_with_hierarchies)
    assert elements[0].metadata.category_depth == 1
    assert elements[1].metadata.category_depth == 2
    assert elements[2].metadata.category_depth is None
    assert elements[3].metadata.category_depth == 0


def test_ocr_data_to_elements(
    filename="example-docs/layout-parser-paper-fast.jpg",
):
    text_regions = [
        TextRegion.from_coords(
            163.0,
            115.0,
            452.0,
            129.0,
            text="LayoutParser: A Unified Toolkit for Deep",
        ),
        TextRegion.from_coords(
            156.0,
            132.0,
            457.0,
            147.0,
            text="Learning Based Document Image Analysis",
        ),
    ]
    ocr_data = [
        LayoutElement(
            bbox=r.bbox,
            text=r.text,
            source=r.source,
            type=ElementType.UNCATEGORIZED_TEXT,
        )
        for r in text_regions
    ]
    image = Image.open(filename)

    elements = common.ocr_data_to_elements(
        ocr_data=ocr_data,
        image_size=image.size,
    )

    assert len(ocr_data) == len(elements)
    assert {el.category for el in elements} == {ElementType.UNCATEGORIZED_TEXT}

    # check coordinates metadata
    image_width, image_height = image.size
    coordinate_system = PixelSpace(width=image_width, height=image_height)
    for el, layout_el in zip(elements, ocr_data):
        assert el.metadata.coordinates == CoordinatesMetadata(
            points=layout_el.bbox.coordinates,
            system=coordinate_system,
        )
