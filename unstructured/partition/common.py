from unstructured.documents.elements import (
    Element,
    CheckBox,
    FigureCaption,
    NarrativeText,
    Text,
    Title,
)


def normalize_layout_element(layout_element) -> Element:
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
    elif element_type == "Checked":
        return CheckBox(checked=True, coordinates=coordinates)
    elif element_type == "Unchecked":
        return CheckBox(checked=False, coordinates=coordinates)
    else:
        return Text(text=text, coordinates=coordinates)
