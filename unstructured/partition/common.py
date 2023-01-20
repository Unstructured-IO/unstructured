from typing import List, Union

from unstructured.documents.elements import (
    Element,
    CheckBox,
    FigureCaption,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.nlp.patterns import UNICODE_BULLETS_RE, ENUMERATED_BULLETS_RE


def normalize_layout_element(layout_element) -> Union[Element, List[Element]]:
    """Converts a list of unstructured_inference DocumentLayout objects to a list of
    unstructured Elements."""

    if not isinstance(layout_element, dict):
        layout_dict = layout_element.to_dict()
    else:
        layout_dict = layout_element

    text = layout_dict["text"]
    coordinates = layout_dict["coordinates"]
    element_type = layout_dict["type"]

    if element_type == "Title":
        return Title(text=text, coordinates=coordinates)
    elif element_type == "Text":
        return NarrativeText(text=text, coordinates=coordinates)
    elif element_type == "Figure":
        return FigureCaption(text=text, coordinates=coordinates)
    elif element_type == "List":
        return layout_list_to_list_items(text, coordinates)
    elif element_type == "Checked":
        return CheckBox(checked=True, coordinates=coordinates)
    elif element_type == "Unchecked":
        return CheckBox(checked=False, coordinates=coordinates)
    else:
        return Text(text=text, coordinates=coordinates)


def layout_list_to_list_items(text: str, coordinates: List[float]) -> List[Element]:
    """Converts a list LayoutElement to a list of ListItem elements."""
    split_items = ENUMERATED_BULLETS_RE.split(text)
    # NOTE(robinson) - this means there wasn't a match for the enumerated bullets
    if len(split_items) == 1:
        split_items = UNICODE_BULLETS_RE.split(text)

    list_items: List[Element] = list()
    for text_segment in split_items:
        if len(text_segment.strip()) > 0:
            list_items.append(ListItem(text=text_segment.strip(), coordinates=coordinates))

    return list_items
