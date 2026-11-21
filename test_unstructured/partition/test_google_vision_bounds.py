import numpy as np
import pytest
from google.cloud.vision import TextAnnotation

from unstructured.partition.utils.ocr_models.google_vision_ocr import OCRAgentGoogleVision


@pytest.mark.parametrize(
    ("vertices", "expected"),
    [
        ([(20, 0), (100, 40), (80, 80), (0, 40)], [0, 0, 100, 80]),
        ([(100, 80), (0, 80), (0, 0), (100, 0)], [0, 0, 100, 80]),
        ([(0, 20), (40, 0), (80, 80), (40, 100)], [0, 0, 80, 100]),
        ([(10, 20), (90, 20), (90, 80), (10, 80)], [10, 20, 90, 80]),
    ],
)
def test_rotated_paragraph_bounds_include_all_vertices(vertices, expected):
    document = TextAnnotation(
        pages=[
            {
                "blocks": [
                    {
                        "paragraphs": [
                            {
                                "bounding_box": {
                                    "vertices": [{"x": x, "y": y} for x, y in vertices]
                                },
                                "words": [
                                    {
                                        "symbols": [
                                            {
                                                "text": "x",
                                                "property": {"detected_break": {"type_": 5}},
                                            }
                                        ]
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    )
    agent = object.__new__(OCRAgentGoogleVision)

    regions = agent._parse_regions(document)

    np.testing.assert_array_equal(regions.element_coords, [expected])
    assert list(regions.texts) == ["x"]
