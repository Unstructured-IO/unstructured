import unstructured.staging.label_studio as label_studio

from unstructured.documents.elements import Title, NarrativeText


def test_convert_to_label_studio_data():
    elements = [Title(text="Title 1"), NarrativeText(text="Narrative 1")]
    label_studio_data = label_studio.stage_for_label_studio(elements)

    assert label_studio_data[0]["data"]["my_text"] == "Title 1"
    assert "ref_id" in label_studio_data[0]["data"]

    assert label_studio_data[1]["data"]["my_text"] == "Narrative 1"
    assert "ref_id" in label_studio_data[1]["data"]
