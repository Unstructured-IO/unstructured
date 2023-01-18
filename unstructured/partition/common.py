from unstructured.documents.elements import FigureCaption, NarrativeText, Text, Title


def layout_element_to_text_element(layout_element) -> Text:
    """Converts a list of unstructured_inference DocumentLayout objects to a list of
    unstructured Elements."""

    if not isinstance(layout_element, dict):
        layout_dict = layout_element.to_dict()
    else:
        layout_dict = layout_element

    text = layout_dict["text"]
    coordinates = layout_dict["coordinates"]
    text_type = layout_dict["type"]

    if text_type == "Title":
        return Title(text=text, coordinates=coordinates)
    elif text_type == "Text":
        return NarrativeText(text=text, coordinates=coordinates)
    elif text_type == "Figure":
        return FigureCaption(text=text, coordinates=coordinates)
    else:
        return Text(text=text, coordinates=coordinates)
