"""Empty JSON pages retain the tensor columns needed for detection evaluation."""

import json
import math

import pytest

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


def load_pages(tmp_path, page_flags):
    """Load matching file formats with independently empty predictions and targets."""
    paths = []
    for column, filename in enumerate(("predictions.json", "targets.json")):
        pages = [
            {
                "number": index + 1,
                "size": {"height": 100, "width": 100},
                "elements": [{"type": "Text", "bbox": [10, 20, 30, 40], "prob": 0.9 - index * 0.1}]
                if flags[column]
                else [],
            }
            for index, flags in enumerate(page_flags)
        ]
        path = tmp_path / filename
        path.write_text(
            json.dumps({"object_detection_classes": ["Text"], "pages": pages}), encoding="utf-8"
        )
        paths.append(path)
    return ObjectDetectionEvalProcessor.from_json_files(*paths)


@pytest.mark.parametrize(
    ("predicted", "target"), [(False, False), (False, True), (True, False), (True, True)]
)
def test_single_page_keeps_empty_prediction_and_target_columns(tmp_path, predicted, target):
    processor = load_pages(tmp_path, [(predicted, target)])

    aggregate, per_class = processor.get_metrics()

    assert processor.document_preds[0].shape == (int(predicted), 6)
    assert processor.document_targets[0].shape == (int(target), 5)
    if target:
        expected = float(predicted)
        assert vars(aggregate) == pytest.approx(
            {"precision": expected, "recall": expected, "f1_score": expected, "m_ap": expected}
        )
        for values in vars(per_class).values():
            assert values == pytest.approx({"Text": expected})
    else:
        assert all(math.isnan(value) for value in vars(aggregate).values())
        assert all(math.isnan(values["Text"]) for values in vars(per_class).values())


@pytest.mark.parametrize("blank_position", [0, 1, 2])
def test_a_blank_page_does_not_change_document_metrics(tmp_path, blank_position):
    pages = [(True, True), (True, True)]
    pages.insert(blank_position, (False, False))

    aggregate, _ = load_pages(tmp_path, pages).get_metrics()

    assert vars(aggregate) == pytest.approx({"precision": 1, "recall": 1, "f1_score": 1, "m_ap": 1})


def test_page_without_predictions_counts_its_target_as_a_false_negative(tmp_path):
    aggregate, _ = load_pages(tmp_path, [(False, True), (True, True)]).get_metrics()

    assert aggregate.precision == pytest.approx(1)
    assert aggregate.recall == pytest.approx(0.5)
    assert aggregate.f1_score == pytest.approx(2 / 3)
    assert aggregate.m_ap == pytest.approx(51 / 101)


def test_page_without_targets_counts_its_prediction_as_a_false_positive(tmp_path):
    aggregate, _ = load_pages(tmp_path, [(True, False), (True, True)]).get_metrics()

    assert aggregate.precision == pytest.approx(0.5)
    assert aggregate.recall == pytest.approx(1)
    assert aggregate.f1_score == pytest.approx(2 / 3)
    assert aggregate.m_ap == pytest.approx(0.5)


def test_document_without_pages_keeps_existing_sentinel_metrics(tmp_path):
    aggregate, _ = load_pages(tmp_path, []).get_metrics()

    assert vars(aggregate) == {"precision": -1, "recall": -1, "f1_score": -1, "m_ap": -1}
