from unstructured.documents.elements import Element, NoID, Text


def test_text_id():
    text_element = Text(text="hello there!")
    assert text_element.id == "c69509590d81db2f37f9d75480c8efed"


def test_element_defaults_to_blank_id():
    element = Element()
    assert isinstance(element.id, NoID)
