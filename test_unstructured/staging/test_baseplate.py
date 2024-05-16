from test_unstructured.unit_utils import assign_hash_ids
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    ElementMetadata,
    NarrativeText,
    Title,
)
from unstructured.staging.baseplate import stage_for_baseplate


def test_stage_for_baseplate():
    points = (
        (545.0150947570801, 226.5191650390625),
        (545.0150947570801, 254.7656043600921),
        (704.879451751709, 254.7656043600921),
        (704.879451751709, 226.5191650390625),
    )
    system = PixelSpace(width=1700, height=2200)
    coordinates_metadata = CoordinatesMetadata(points=points, system=system)
    metadata = ElementMetadata(filename="fox.pdf", coordinates=coordinates_metadata)
    elements = assign_hash_ids(
        [
            Title("A Wonderful Story About A Fox", metadata=metadata),
            NarrativeText(
                "A fox ran into the chicken coop and the chickens flew off!", metadata=metadata
            ),
        ]
    )

    rows = stage_for_baseplate(elements)
    assert rows == {
        "rows": [
            {
                "data": {
                    "element_id": "933d9fce18f44b09f4ec6975f470a0d7",
                    "text": "A Wonderful Story About A Fox",
                    "type": "Title",
                },
                "metadata": {
                    "filename": "fox.pdf",
                    "coordinates_points": (
                        (545.0150947570801, 226.5191650390625),
                        (545.0150947570801, 254.7656043600921),
                        (704.879451751709, 254.7656043600921),
                        (704.879451751709, 226.5191650390625),
                    ),
                    "coordinates_system": "PixelSpace",
                    "coordinates_layout_width": 1700,
                    "coordinates_layout_height": 2200,
                },
            },
            {
                "data": {
                    "element_id": "d154ec57da0d7d4439aaed8ec6546f6e",
                    "text": "A fox ran into the chicken coop and the chickens flew off!",
                    "type": "NarrativeText",
                },
                "metadata": {
                    "filename": "fox.pdf",
                    "coordinates_points": (
                        (545.0150947570801, 226.5191650390625),
                        (545.0150947570801, 254.7656043600921),
                        (704.879451751709, 254.7656043600921),
                        (704.879451751709, 226.5191650390625),
                    ),
                    "coordinates_system": "PixelSpace",
                    "coordinates_layout_width": 1700,
                    "coordinates_layout_height": 2200,
                },
            },
        ],
    }
