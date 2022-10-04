import pytest
import unstructured.staging.label_studio as label_studio

from unstructured.documents.elements import Title, NarrativeText

from label_studio_sdk.client import Client

# import requests
# import logging

# log = logging.getLogger("urllib3")  # works
# import pytest

# log.setLevel(logging.DEBUG)  # needed
# fh = logging.FileHandler("requests.log")
# log.addHandler(fh)
# logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


class MockResponse:
    def __init__(self, *args, **kwargs):
        self.headers = dict()
        self.status_code = 201

    def json(self):
        return {"task_ids": None}


def test_upload_label_studio_data_with_sdk(monkeypatch, elements):
    monkeypatch.setattr(Client, "make_request", MockResponse)
    client = Client(url="http://fake.url", api_key="fake_key")
    # Connect to the Label Studio API and check the connection
    client.check_connection()
    # Create a new project
    project = client.start_project()
    project.id = 1
    # Upload data to the project
    label_studio_data = label_studio.stage_for_label_studio(elements)
    # task_ids = MockResponse.json()["task_ids"] based on SDK
    task_ids = project.import_tasks(label_studio_data)
    assert not task_ids


# def test_real_sdk(elements):
#     # Need to run label studio instance

#     # Define the URL where Label Studio is accessible and the API key for your user account
#     LABEL_STUDIO_URL = "http://localhost:8080"
#     API_KEY = "d44b92c31f592583bffb7e0d817a60c16a937bca"
#     # Connect to the Label Studio API and check the connection
#     ls = Client(url=LABEL_STUDIO_URL, api_key=API_KEY)
#     ls.check_connection()
#     project = ls.get_projects()[0]
#     label_studio_data = label_studio.stage_for_label_studio(elements)
#     project.import_tasks(label_studio_data)
#     # project.import_tasks(
#     #     [{'data': {'my_text': 'Title 1', 'ref_id': 'ab03af41c2940e7584b62df48a964db3'}},
#     #     {'data': {'my_text': 'Narrative 1', 'ref_id': 'ff9eb806beb1f483322f6fbda680b08b'}}]
#     # )


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
