import pathlib
from dataclasses import dataclass
from multiprocessing import Pool
from unittest import mock

import numpy as np
import pytest
from PIL import Image
from unstructured_inference.inference import layout
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElement

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    CoordinatesMetadata,
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
from unstructured.partition.common import common
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_DONT, SORT_MODE_XY_CUT


class MockPageLayout(layout.PageLayout):
    def __init__(self, number: int, image: Image.Image):
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


@pytest.mark.parametrize(
    ("element_type", "expected_element_class"),
    TYPE_TO_TEXT_ELEMENT_MAP.items(),
)
def test_normalize_layout_element_layout_element_maps_to_appropriate_text_element(
    element_type: str,
    expected_element_class: type[Text],
):
    layout_element = LayoutElement.from_coords(
        type=element_type,
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
    assert element == expected_element_class(
        text="Some lovely text",
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
        coordinate_system=coordinate_system,
    )


@pytest.mark.parametrize(
    ("element_type", "expected_checked"),
    [
        (ElementType.CHECK_BOX_UNCHECKED, False),
        (ElementType.CHECK_BOX_CHECKED, True),
        (ElementType.RADIO_BUTTON_UNCHECKED, False),
        (ElementType.RADIO_BUTTON_CHECKED, True),
        (ElementType.CHECKED, True),
        (ElementType.UNCHECKED, False),
    ],
)
def test_normalize_layout_element_checkable(element_type: str, expected_checked: bool):
    layout_element = LayoutElement.from_coords(
        type=element_type,
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
    assert isinstance(element, CheckBox)
    assert element == CheckBox(
        checked=expected_checked,
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


class MockRunOutput:

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_convert_office_doc_captures_errors(monkeypatch, caplog):
    from unstructured.partition.common.common import subprocess

    def mock_run(*args, **kwargs):
        return MockRunOutput(1, "an error occurred".encode(), "error details".encode())

    monkeypatch.setattr(subprocess, "run", mock_run)
    common.convert_office_doc("no-real.docx", "fake-directory", target_format="docx")
    assert "soffice failed to convert to format docx with code 1" in caplog.text


def test_convert_office_docs_avoids_concurrent_call_to_soffice():
    paths_to_save = [pathlib.Path(path) for path in ("/tmp/proc1", "/tmp/proc2", "/tmp/proc3")]
    for path in paths_to_save:
        path.mkdir(exist_ok=True)
        (path / "simple.docx").unlink(missing_ok=True)
    file_to_convert = example_doc_path("simple.doc")

    with Pool(3) as pool:
        pool.starmap(common.convert_office_doc, [(file_to_convert, path) for path in paths_to_save])

    assert np.sum([(path / "simple.docx").is_file() for path in paths_to_save]) == 3


def test_convert_office_docs_respects_wait_timeout():
    paths_to_save = [
        pathlib.Path(path) for path in ("/tmp/wait/proc1", "/tmp/wait/proc2", "/tmp/wait/proc3")
    ]
    for path in paths_to_save:
        path.mkdir(parents=True, exist_ok=True)
        (path / "simple.docx").unlink(missing_ok=True)
    file_to_convert = example_doc_path("simple.doc")

    with Pool(3) as pool:
        pool.starmap(
            common.convert_office_doc,
            # set timeout to wait for soffice to be available to 0 so only one process can convert
            # the doc file on the first try; then the catch all
            [(file_to_convert, path, "docx", None, 0) for path in paths_to_save],
        )

    # because this test file is very small we could have occasions where two files are converted
    # when one of the processes spawned just a little
    assert np.sum([(path / "simple.docx").is_file() for path in paths_to_save]) < 3


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
    filename=example_doc_path("img/layout-parser-paper-fast.jpg"),
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
