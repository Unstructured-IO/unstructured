from unstructured_inference.inference.layout import LayoutElement

from unstructured.documents.elements import (
    CheckBox,
    FigureCaption,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.partition import common


def test_normalize_layout_element_dict():
    layout_element = {
        "type": "Title",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "coordinate_system": None,
        "text": "Some lovely text",
    }
    element = common.normalize_layout_element(layout_element)
    assert element == Title(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
        coordinate_system=None,
    )


def test_normalize_layout_element_dict_caption():
    layout_element = {
        "type": "Figure",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    element = common.normalize_layout_element(layout_element)
    assert element == FigureCaption(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
    )


def test_normalize_layout_element_dict_figure_caption():
    layout_element = {
        "type": "FigureCaption",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    element = common.normalize_layout_element(layout_element)
    assert element == FigureCaption(
        text="Some lovely text",
        coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]],
    )


def test_normalize_layout_element_dict_misc():
    layout_element = {
        "type": "Misc",
        "coordinates": [[1, 2], [3, 4], [5, 6], [7, 8]],
        "text": "Some lovely text",
    }
    element = common.normalize_layout_element(layout_element)
    assert element == Text(text="Some lovely text", coordinates=[[1, 2], [3, 4], [5, 6], [7, 8]])


def test_normalize_layout_element_layout_element():
    layout_element = LayoutElement(
        type="Text",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="Some lovely text",
    )
    element = common.normalize_layout_element(layout_element)
    assert element == NarrativeText(
        text="Some lovely text",
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
    )


def test_normalize_layout_element_layout_element_narrative_text():
    layout_element = LayoutElement(
        type="NarrativeText",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="Some lovely text",
    )
    element = common.normalize_layout_element(layout_element)
    assert element == NarrativeText(
        text="Some lovely text",
        coordinates=((1, 2), (1, 4), (3, 4), (3, 2)),
    )


def test_normalize_layout_element_checked_box():
    layout_element = LayoutElement(
        type="Checked",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="",
    )
    element = common.normalize_layout_element(layout_element)
    assert element == CheckBox(checked=True, coordinates=((1, 2), (1, 4), (3, 4), (3, 2)))


def test_normalize_layout_element_unchecked_box():
    layout_element = LayoutElement(
        type="Unchecked",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="",
    )
    element = common.normalize_layout_element(layout_element)
    assert element == CheckBox(checked=False, coordinates=((1, 2), (1, 4), (3, 4), (3, 2)))


def test_normalize_layout_element_enumerated_list():
    layout_element = LayoutElement(
        type="List",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="1. I'm so cool! 2. You're cool too. 3. We're all cool!",
    )
    elements = common.normalize_layout_element(layout_element)
    assert elements == [
        ListItem(text="I'm so cool!", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
        ListItem(text="You're cool too.", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
        ListItem(text="We're all cool!", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
    ]


def test_normalize_layout_element_bulleted_list():
    layout_element = LayoutElement(
        type="List",
        x1=1,
        y1=2,
        x2=3,
        y2=4,
        text="* I'm so cool! * You're cool too. * We're all cool!",
    )
    elements = common.normalize_layout_element(layout_element)
    assert elements == [
        ListItem(text="I'm so cool!", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
        ListItem(text="You're cool too.", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
        ListItem(text="We're all cool!", coordinates=((1, 2), (1, 4), (3, 4), (3, 2))),
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
