import logging
import re

import pytest
import vcr
from label_studio_sdk.client import Client

from test_unstructured.unit_utils import assign_hash_ids
from unstructured.documents.elements import NarrativeText, Title
from unstructured.staging import label_studio


@pytest.fixture()
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


@vcr.use_cassette(
    "test_unstructured/vcr_fixtures/cassettes/label_studio_upload.yaml",
    allow_playback_repeats=True,
)
def test_upload_label_studio_data_with_sdk(caplog, elements):
    """
    Testing Instructions
    ====================
    1. Remove file `test_unstructured/vcr_fixtures/cassettes/label_studio_upload.yaml`,
        which will be recreated later.
    2. Install the label-studio package by running command `pip install -U label-studio`.
    3. Run command `label-studio`, and login or set up label studio account on pop-up website.
    4. Update `LABEL_STUDIO_URL` and `API_KEY` below, you can find your API_KEY by
        clicking into your account profile.
    5. Run this test once, and VCR will record the HTTP request to the yaml file.
    6. Kill the label studio instance and run the test again, VCR will replay the response.
    """
    log = logging.getLogger("urllib3")
    log.setLevel(logging.DEBUG)
    # Define the URL where Label Studio is accessible
    LABEL_STUDIO_URL = "http://localhost:8080"
    # API_KEY is a temporary key from local install not actually valid anywhere
    # Update it if the vcr cassette is updated with the API key from your user account
    API_KEY = "7b613506d5afa062fe33c9cd825f106c718b82a0"
    # Connect to the Label Studio API and check the connection
    ls = Client(url=LABEL_STUDIO_URL, api_key=API_KEY)
    ls.check_connection()
    ls.delete_all_projects()
    # Create a sample project to classify types of texts
    project = ls.start_project(
        title="Text Type Classifications",
        label_config="""
        <View>
        <Text name="text" value="$text"/>
        <View style="box-shadow: 2px 2px 5px #999;
                       padding: 20px; margin-top: 2em;
                       border-radius: 5px;">
            <Header value="Choose text type"/>
            <Choices name="type" toName="text"
                    choice="single" showInLine="true">
            <Choice value="Title"/>
              <Choice value="Narrative"/>
            </Choices>
        </View>
        </View>
        """,
    )
    label_studio_data = label_studio.stage_for_label_studio(elements)
    project.import_tasks(label_studio_data)
    # Check success status code (201) for posting tasks job in logger info
    success_posting_tasks_status = re.compile(r"POST /api/projects/.*/import.*201")
    assert bool(success_posting_tasks_status.search(caplog.text))


def test_convert_to_label_studio_data(elements):
    label_studio_data = label_studio.stage_for_label_studio(elements)

    assert label_studio_data[0]["data"]["text"] == "Title 1"
    assert "ref_id" in label_studio_data[0]["data"]

    assert label_studio_data[1]["data"]["text"] == "Narrative 1"
    assert "ref_id" in label_studio_data[1]["data"]


def test_specify_text_name(elements):
    label_studio_data = label_studio.stage_for_label_studio(elements, text_field="random_text")
    assert "random_text" in label_studio_data[0]["data"]
    assert label_studio_data[0]["data"]["random_text"] == "Title 1"


def test_specify_id_name(elements):
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
def test_init_prediction(score, raises, exception):
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
