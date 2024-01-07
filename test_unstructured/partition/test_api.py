import contextlib
import json
import os
import pathlib
from unittest.mock import ANY, Mock

import pytest
import requests
from unstructured_client.general import General

from unstructured.documents.elements import NarrativeText
from unstructured.partition.api import partition_multiple_via_api, partition_via_api

DIRECTORY = pathlib.Path(__file__).parent.resolve()

EML_TEST_FILE = "eml/fake-email.eml"

skip_outside_ci = os.getenv("CI", "").lower() in {"", "false", "f", "0"}
skip_not_on_main = os.getenv("GITHUB_REF_NAME", "").lower() != "main"

MOCK_TEXT = """[
    {
        "element_id": "f49fbd614ddf5b72e06f59e554e6ae2b",
        "text": "This is a test email to use for unit tests.",
        "type": "NarrativeText",
        "metadata": {
            "sent_from": [
                "Matthew Robinson <mrobinson@unstructured.io>"
            ],
            "sent_to": [
                "Matthew Robinson <mrobinson@unstructured.io>"
            ],
            "subject": "Test Email",
            "filename": "fake-email.eml",
            "filetype": "message/rfc822"
        }
    }
]"""


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        # string representation of partitioned elements is nested in an additional
        # layer in the new unstructured-client:
        #     `elements_from_json(text=response.raw_response.text)`
        self.raw_response = MockRawResponse()
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return json.loads(self.text)

    @property
    def text(self):
        return MOCK_TEXT


class MockRawResponse:
    def __init__(self):
        self.text = MOCK_TEXT


def test_partition_via_api_from_filename(monkeypatch):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)
    elements = partition_via_api(filename=filename)
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0].metadata.filetype == "message/rfc822"


def test_partition_via_api_custom_url(monkeypatch):
    """
    Assert that we can specify api_url and requests are sent to the right place
    """
    mock_request = Mock(return_value=MockResponse(status_code=200))

    monkeypatch.setattr(requests.Session, "request", mock_request)
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)
    custom_url = "http://localhost:8000/general/v0/general"

    with open(filename, "rb") as f:
        partition_via_api(file=f, api_url=custom_url, metadata_filename=filename)

    mock_request.assert_called_with(
        "POST", custom_url, data=ANY, files=ANY, headers=ANY, params=ANY
    )

    # The sdk uses the server url, so we should be able to pass that as well
    base_url = "http://localhost:8000"

    with open(filename, "rb") as f:
        partition_via_api(file=f, api_url=base_url, metadata_filename=filename)

    mock_request.assert_called_with(
        "POST", custom_url, data=ANY, files=ANY, headers=ANY, params=ANY
    )


def test_partition_via_api_from_file(monkeypatch):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    with open(filename, "rb") as f:
        elements = partition_via_api(file=f, metadata_filename=filename)
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0].metadata.filetype == "message/rfc822"


def test_partition_via_api_from_file_warns_with_file_filename(monkeypatch, caplog):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    with open(filename, "rb") as f:
        partition_via_api(file=f, file_filename=filename)

    assert "WARNING" in caplog.text
    assert "The file_filename kwarg will be deprecated" in caplog.text


def test_partition_via_api_from_file_raises_with_metadata_and_file_filename(monkeypatch):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_via_api(file=f, file_filename=filename, metadata_filename=filename)


def test_partition_via_api_from_file_raises_without_filename(monkeypatch):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_via_api(file=f)


def test_partition_via_api_raises_with_bad_response(monkeypatch):
    monkeypatch.setattr(
        General,
        "partition",
        lambda *args, **kwargs: MockResponse(status_code=500),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    with pytest.raises(ValueError):
        partition_via_api(filename=filename)


@pytest.mark.skipif(skip_outside_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_with_no_strategy():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf")

    elements_no_strategy = partition_via_api(
        filename=filename,
        strategy="auto",
        api_key=get_api_key(),
    )
    elements_hi_res = partition_via_api(filename=filename, strategy="hi_res", api_key=get_api_key())

    # confirm that hi_res strategy was not passed as default to partition by comparing outputs
    # elements_hi_res[3].text =
    #     'LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis'
    # while elements_no_strategy[3].text = ']' (as of this writing)
    assert elements_no_strategy[3].text != elements_hi_res[3].text


@pytest.mark.skipif(skip_outside_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_with_image_hi_res_strategy_includes_coordinates():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.jpg")

    # coordinates not included by default to limit payload size
    elements = partition_via_api(
        filename=filename,
        strategy="hi_res",
        coordinates="true",
        api_key=get_api_key(),
    )

    assert elements[0].metadata.coordinates is not None


@pytest.mark.skipif(skip_outside_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_valid_request_data_kwargs():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf")

    elements = partition_via_api(filename=filename, strategy="fast", api_key=get_api_key())

    assert isinstance(elements, list)


# Note(austin) - This test is way too noisy against the hosted api
# def test_partition_via_api_invalid_request_data_kwargs():
#     filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf")
#     with pytest.raises(SDKError):
#         partition_via_api(filename=filename, strategy="not_a_strategy")


class MockMultipleResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)

    @property
    def text(self):
        return """[
    [
        {
            "element_id": "f49fbd614ddf5b72e06f59e554e6ae2b",
            "text": "This is a test email to use for unit tests.",
            "type": "NarrativeText",
            "metadata": {
                "sent_from": [
                    "Matthew Robinson <mrobinson@unstructured.io>"
                ],
                "sent_to": [
                    "Matthew Robinson <mrobinson@unstructured.io>"
                ],
                "subject": "Test Email",
                "filename": "fake-email.eml",
                "filetype": "message/rfc822"
            }
        }
    ],
    [
        {
            "element_id": "f49fbd614ddf5b72e06f59e554e6ae2b",
            "text": "This is a test email to use for unit tests.",
            "type": "NarrativeText",
            "metadata": {
                "sent_from": [
                    "Matthew Robinson <mrobinson@unstructured.io>"
                ],
                "sent_to": [
                    "Matthew Robinson <mrobinson@unstructured.io>"
                ],
                "subject": "Test Email",
                "filename": "fake-email.eml",
                "filetype": "message/rfc822"
            }
        }
    ]
]"""


def test_partition_multiple_via_api_with_single_filename(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE)

    elements = partition_multiple_via_api(filenames=[filename])
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_from_filenames(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", "eml/fake-email.eml"),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    elements = partition_multiple_via_api(filenames=filenames)
    assert len(elements) == 2
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_from_files(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        elements = partition_multiple_via_api(
            files=files,
            metadata_filenames=filenames,
        )
    assert len(elements) == 2
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_warns_with_file_filename(monkeypatch, caplog):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        partition_multiple_via_api(
            files=files,
            file_filenames=filenames,
        )
    assert "WARNING" in caplog.text
    assert "The file_filenames kwarg will be deprecated" in caplog.text


def test_partition_multiple_via_api_warns_with_file_and_metadata_filename(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        with pytest.raises(ValueError):
            partition_multiple_via_api(
                files=files,
                metadata_filenames=filenames,
                file_filenames=filenames,
            )


def test_partition_multiple_via_api_raises_with_bad_response(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=500),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with pytest.raises(ValueError):
        partition_multiple_via_api(filenames=filenames)


def test_partition_multiple_via_api_raises_with_content_types_size_mismatch(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=500),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml"),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with pytest.raises(ValueError):
        partition_multiple_via_api(
            filenames=filenames,
            content_types=["text/plain"],
        )


def test_partition_multiple_via_api_from_files_raises_with_size_mismatch(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        with pytest.raises(ValueError):
            partition_multiple_via_api(
                files=files,
                metadata_filenames=filenames,
                content_types=["text/plain"],
            )


def test_partition_multiple_via_api_from_files_raises_without_filenames(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockMultipleResponse(status_code=200),
    )

    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", EML_TEST_FILE),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "fake.docx"),
    ]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        with pytest.raises(ValueError):
            partition_multiple_via_api(
                files=files,
            )


def get_api_key():
    api_key = os.getenv("UNS_API_KEY")
    if api_key is None:
        raise ValueError("UNS_API_KEY environment variable not set")
    return api_key


@pytest.mark.skipif(skip_outside_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_multiple_via_api_valid_request_data_kwargs():
    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf"),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.jpg"),
    ]

    elements = partition_multiple_via_api(
        filenames=filenames,
        strategy="auto",
        api_key=get_api_key(),
    )
    assert isinstance(elements, list)


@pytest.mark.skipif(skip_outside_ci, reason="Skipping test run outside of CI")
def test_partition_multiple_via_api_invalid_request_data_kwargs():
    filenames = [
        os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf"),
        os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.jpg"),
    ]
    with pytest.raises(ValueError):
        partition_multiple_via_api(
            filenames=filenames,
            strategy="not_a_strategy",
            api_key=get_api_key(),
        )
