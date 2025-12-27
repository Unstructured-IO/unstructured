from __future__ import annotations

import pytest

from test_unstructured.unit_utils import assign_hash_ids
from unstructured.documents.elements import Element, NarrativeText, Title
from unstructured.staging import label_studio


@pytest.fixture()
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


def test_convert_to_label_studio_data(elements: list[Element]):
    label_studio_data = label_studio.stage_for_label_studio(elements)

    assert label_studio_data[0]["data"]["text"] == "Title 1"
    assert "ref_id" in label_studio_data[0]["data"]

    assert label_studio_data[1]["data"]["text"] == "Narrative 1"
    assert "ref_id" in label_studio_data[1]["data"]


def test_specify_text_name(elements: list[Element]):
    label_studio_data = label_studio.stage_for_label_studio(elements, text_field="random_text")
    assert "random_text" in label_studio_data[0]["data"]
    assert label_studio_data[0]["data"]["random_text"] == "Title 1"


def test_specify_id_name(elements: list[Element]):
    label_studio_data = label_studio.stage_for_label_studio(elements, id_field="random_id")
    assert "random_id" in label_studio_data[0]["data"]


def test_created_annotation():
    annotation = label_studio.LabelStudioAnnotation(
        result=[
            label_studio.LabelStudioResult(
                type="choices",
                value={"choices": ["Positive"]},
                from_name="sentiment",
                to_name="text",
            ),
        ],
    )

    annotation.to_dict() == {
        "result": [
            {
                "type": "choices",
                "value": {"choices": ["Positive"]},
                "from_name": "sentiment",
                "id": None,
                "to_name": "text",
                "hidden": False,
                "read_only": False,
            },
        ],
        "was_canceled": False,
    }


@pytest.mark.parametrize(
    ("score", "raises", "exception"),
    [
        (None, True, ValueError),
        (-0.25, True, ValueError),
        (0, False, None),
        (0.5, False, None),
        (1, False, None),
        (1.25, True, ValueError),
    ],
)
def test_init_prediction(score: float | None, raises: bool, exception: Exception | None):
    result = [
        label_studio.LabelStudioResult(
            type="choices",
            value={"choices": ["Positive"]},
            from_name="sentiment",
            to_name="text",
        ),
    ]

    if raises:
        with pytest.raises(exception):
            label_studio.LabelStudioPrediction(result=result, score=score)
    else:
        prediction = label_studio.LabelStudioPrediction(result=result, score=score)
        prediction.to_dict() == {
            "result": [
                {
                    "type": "choices",
                    "value": {"choices": ["Positive"]},
                    "from_name": "sentiment",
                    "id": None,
                    "to_name": "text",
                    "hidden": False,
                    "read_only": False,
                },
            ],
            "was_canceled": False,
            "score": score,
        }


def test_stage_with_annotation():
    elements = assign_hash_ids([NarrativeText(text="A big brown bear")])
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                ),
            ],
        ),
    ]
    label_studio_data = label_studio.stage_for_label_studio(elements, [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "2812a3676591a479c5425789f9c0156f"},
            "annotations": [
                {
                    "result": [
                        {
                            "type": "choices",
                            "value": {"choices": ["Positive"]},
                            "from_name": "sentiment",
                            "id": None,
                            "to_name": "text",
                            "hidden": False,
                            "read_only": False,
                        },
                    ],
                    "was_canceled": False,
                },
            ],
        },
    ]


def test_stage_with_prediction():
    elements = assign_hash_ids([NarrativeText(text="A big brown bear")])

    prediction = [
        label_studio.LabelStudioPrediction(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                ),
            ],
            score=0.98,
        ),
    ]
    label_studio_data = label_studio.stage_for_label_studio(elements, predictions=[prediction])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "2812a3676591a479c5425789f9c0156f"},
            "predictions": [
                {
                    "result": [
                        {
                            "type": "choices",
                            "value": {"choices": ["Positive"]},
                            "from_name": "sentiment",
                            "id": None,
                            "to_name": "text",
                            "hidden": False,
                            "read_only": False,
                        },
                    ],
                    "was_canceled": False,
                    "score": 0.98,
                },
            ],
        },
    ]


def test_stage_with_annotation_for_ner():
    elements = assign_hash_ids([NarrativeText(text="A big brown bear")])

    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="labels",
                    value={"start": 12, "end": 16, "text": "bear", "labels": ["PER"]},
                    from_name="label",
                    to_name="text",
                ),
            ],
        ),
    ]
    label_studio_data = label_studio.stage_for_label_studio(elements, [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "2812a3676591a479c5425789f9c0156f"},
            "annotations": [
                {
                    "result": [
                        {
                            "type": "labels",
                            "value": {"start": 12, "end": 16, "text": "bear", "labels": ["PER"]},
                            "from_name": "label",
                            "id": None,
                            "to_name": "text",
                            "hidden": False,
                            "read_only": False,
                        },
                    ],
                    "was_canceled": False,
                },
            ],
        },
    ]


def test_stage_with_annotation_raises_with_mismatched_lengths():
    element = NarrativeText(text="A big brown bear")
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                ),
            ],
        ),
    ]
    with pytest.raises(ValueError):
        label_studio.stage_for_label_studio([element], [annotations, annotations])


def test_stage_with_prediction_raises_with_mismatched_lengths():
    element = NarrativeText(text="A big brown bear")
    prediction = [
        label_studio.LabelStudioPrediction(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                ),
            ],
            score=0.82,
        ),
    ]
    with pytest.raises(ValueError):
        label_studio.stage_for_label_studio([element], predictions=[prediction, prediction])


def test_stage_with_annotation_raises_with_invalid_type():
    with pytest.raises(ValueError):
        label_studio.LabelStudioResult(
            type="bears",
            value={"bears": ["Positive"]},
            from_name="sentiment",
            to_name="text",
        )


def test_stage_with_reviewed_annotation():
    elements = assign_hash_ids([NarrativeText(text="A big brown bear")])
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                ),
            ],
            reviews=[label_studio.LabelStudioReview(created_by={"user_id": 1}, accepted=True)],
        ),
    ]
    label_studio_data = label_studio.stage_for_label_studio(elements, [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "2812a3676591a479c5425789f9c0156f"},
            "annotations": [
                {
                    "result": [
                        {
                            "type": "choices",
                            "value": {"choices": ["Positive"]},
                            "from_name": "sentiment",
                            "to_name": "text",
                            "id": None,
                            "hidden": False,
                            "read_only": False,
                        },
                    ],
                    "reviews": [{"created_by": {"user_id": 1}, "accepted": True, "id": None}],
                    "was_canceled": False,
                },
            ],
        },
    ]
