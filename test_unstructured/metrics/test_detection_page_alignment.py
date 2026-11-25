"""Detection files identify pages by number, independently of their JSON list order."""

import json

import pytest

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


def write_document(path, order):
    """Write perfect detections on pages with different sizes and disjoint boxes."""
    pages = {
        1: {"size": {"height": 100, "width": 100}, "box": [1, 2, 10, 20], "type": "Text"},
        2: {"size": {"height": 200, "width": 200}, "box": [120, 130, 160, 170], "type": "Text"},
        3: {"size": {"height": 300, "width": 300}, "box": [230, 240, 260, 280], "type": "Title"},
    }
    path.write_text(
        json.dumps(
            {
                "object_detection_classes": ["Text", "Title"],
                "pages": [
                    {
                        "number": number,
                        "size": pages[number]["size"],
                        "elements": [
                            {
                                "type": pages[number]["type"],
                                "bbox": pages[number]["box"],
                                "prob": 0.9,
                            }
                        ],
                    }
                    for number in order
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("prediction_order", [(1, 2, 3), (3, 2, 1), (2, 3, 1)])
@pytest.mark.parametrize("target_order", [(1, 2, 3), (3, 2, 1), (2, 3, 1)])
def test_perfect_detection_metrics_do_not_depend_on_page_list_order(
    tmp_path, prediction_order, target_order
):
    prediction_path = tmp_path / "predictions.json"
    target_path = tmp_path / "targets.json"
    write_document(prediction_path, prediction_order)
    write_document(target_path, target_order)
    before = (prediction_path.read_bytes(), target_path.read_bytes())

    processor = ObjectDetectionEvalProcessor.from_json_files(prediction_path, target_path)
    aggregate, per_class = processor.get_metrics()

    assert vars(aggregate) == pytest.approx({"f1_score": 1, "precision": 1, "recall": 1, "m_ap": 1})
    for scores in vars(per_class).values():
        assert scores == pytest.approx({"Text": 1, "Title": 1})
    assert (prediction_path.read_bytes(), target_path.read_bytes()) == before


def test_single_page_metrics_keep_existing_behavior(tmp_path):
    prediction_path = tmp_path / "predictions.json"
    target_path = tmp_path / "targets.json"
    write_document(prediction_path, (2,))
    write_document(target_path, (2,))

    aggregate, _ = ObjectDetectionEvalProcessor.from_json_files(
        prediction_path, target_path
    ).get_metrics()

    assert vars(aggregate) == pytest.approx({"f1_score": 1, "precision": 1, "recall": 1, "m_ap": 1})


def test_different_page_numbers_are_still_rejected(tmp_path):
    prediction_path = tmp_path / "predictions.json"
    target_path = tmp_path / "targets.json"
    write_document(prediction_path, (2, 1))
    write_document(target_path, (3, 1))

    with pytest.raises(AssertionError, match="Page numbers"):
        ObjectDetectionEvalProcessor.from_json_files(prediction_path, target_path)
