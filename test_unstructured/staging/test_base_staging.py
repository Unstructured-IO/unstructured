import unstructured.staging.base as base

from unstructured.documents.elements import Title, NarrativeText


def test_convert_to_isd():
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    isd = base.convert_to_isd(elements)

    assert isd[0]["text"] == "Title 1"
    assert isd[0]["type"] == "Title"

    assert isd[1]["text"] == "Narrative 1"
    assert isd[1]["type"] == "NarrativeText"
