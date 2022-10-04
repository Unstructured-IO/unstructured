import pytest
import unstructured.staging.label_studio as label_studio

from unstructured.documents.elements import Title, NarrativeText

from label_studio_sdk.client import Client

import logging
import re


@pytest.fixture
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


def test_upload_label_studio_data_with_sdk_on_real_instance(caplog, elements):
    log = logging.getLogger("urllib3")
    log.setLevel(logging.DEBUG)
    # Need to run label studio instance

    # Define the URL where Label Studio is accessible and the API key for your user account
    LABEL_STUDIO_URL = "http://localhost:8080"
    API_KEY = "d44b92c31f592583bffb7e0d817a60c16a937bca"
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
            )
        ]
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
            }
        ],
        "was_canceled": False,
    }


def test_stage_with_annotation():
    element = NarrativeText(text="A big brown bear")
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                )
            ]
        )
    ]
    label_studio_data = label_studio.stage_for_label_studio([element], [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "8f458d5d0635df3975ceb9109cef9e12"},
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
                        }
                    ],
                    "was_canceled": False,
                }
            ],
        }
    ]


def test_stage_with_annotation_for_ner():
    element = NarrativeText(text="A big brown bear")
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="labels",
                    value={"start": 12, "end": 16, "text": "bear", "labels": ["PER"]},
                    from_name="label",
                    to_name="text",
                )
            ]
        )
    ]
    label_studio_data = label_studio.stage_for_label_studio([element], [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "8f458d5d0635df3975ceb9109cef9e12"},
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
                        }
                    ],
                    "was_canceled": False,
                }
            ],
        }
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
                )
            ]
        )
    ]
    with pytest.raises(ValueError):
        label_studio.stage_for_label_studio([element], [annotations, annotations])


def test_stage_with_annotation_raises_with_invalid_type():
    with pytest.raises(ValueError):
        label_studio.LabelStudioResult(
            type="bears",
            value={"bears": ["Positive"]},
            from_name="sentiment",
            to_name="text",
        )


def test_stage_with_reviewed_annotation():
    element = NarrativeText(text="A big brown bear")
    annotations = [
        label_studio.LabelStudioAnnotation(
            result=[
                label_studio.LabelStudioResult(
                    type="choices",
                    value={"choices": ["Positive"]},
                    from_name="sentiment",
                    to_name="text",
                )
            ],
            reviews=[label_studio.LabelStudioReview(created_by={"user_id": 1}, accepted=True)],
        )
    ]
    label_studio_data = label_studio.stage_for_label_studio([element], [annotations])
    assert label_studio_data == [
        {
            "data": {"text": "A big brown bear", "ref_id": "8f458d5d0635df3975ceb9109cef9e12"},
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
                        }
                    ],
                    "reviews": [{"created_by": {"user_id": 1}, "accepted": True, "id": None}],
                    "was_canceled": False,
                }
            ],
        }
    ]
