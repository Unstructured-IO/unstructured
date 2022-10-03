import pytest
import unstructured.staging.label_studio as label_studio

from unstructured.documents.elements import Title, NarrativeText

from label_studio_sdk.client import Client


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
