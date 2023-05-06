from unstructured.documents.elements import ElementMetadata, NarrativeText, Title
from unstructured.staging.baseplate import stage_for_baseplate


def test_stage_for_baseplate():
    metadata = ElementMetadata(filename="fox.epub")
    elements = [
        Title("A Wonderful Story About A Fox", metadata=metadata),
        NarrativeText(
            "A fox ran into the chicken coop and the chickens flew off!",
            metadata=metadata,
        ),
    ]

    rows = stage_for_baseplate(elements)
    assert rows == {
        "rows": [
            {
                "data": {
                    "element_id": "ad270eefd1cc68d15f4d3e51666d4dc8",
                    "coordinates": None,
                    "text": "A Wonderful Story About A Fox",
                    "type": "Title",
                },
                "metadata": {"filename": "fox.epub"},
            },
            {
                "data": {
                    "element_id": "8275769fdd1804f9f2b55ad3c9b0ef1b",
                    "coordinates": None,
                    "text": "A fox ran into the chicken coop and the chickens flew off!",
                    "type": "NarrativeText",
                },
                "metadata": {"filename": "fox.epub"},
            },
        ],
    }
