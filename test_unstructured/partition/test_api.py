import base64
import contextlib
import json
import os
import pathlib
from typing import Any
from unittest.mock import Mock

import pytest
import requests
from unstructured_client.general import General
from unstructured_client.models import shared
from unstructured_client.models.operations import PartitionRequest
from unstructured_client.models.shared import PartitionParameters
from unstructured_client.utils import retries

from unstructured.documents.elements import ElementType, NarrativeText
from unstructured.partition.api import (
    DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC,
    DEFAULT_RETRIES_MAX_INTERVAL_SEC,
    get_retries_config,
    partition_multiple_via_api,
    partition_via_api,
)

from ..unit_utils import ANY, FixtureRequest, example_doc_path, method_mock

DIRECTORY = pathlib.Path(__file__).parent.resolve()

# NOTE(yao): point to paid API for now
API_URL = "https://api.unstructuredapp.io/general/v0/general"

is_in_ci = os.getenv("CI", "").lower() not in {"", "false", "f", "0"}
skip_not_on_main = os.getenv("GITHUB_REF_NAME", "").lower() != "main"


def test_partition_via_api_with_filename_correctly_calls_sdk(
    request: FixtureRequest, expected_call_: list[Any]
):
    partition_mock_ = method_mock(
        request, General, "partition", return_value=FakeResponse(status_code=200)
    )

    elements = partition_via_api(filename=example_doc_path("eml/fake-email.eml"))

    partition_mock_.assert_called_once_with(
        expected_call_[0], request=expected_call_[1], retries=expected_call_[2]
    )
    assert isinstance(partition_mock_.call_args_list[0].args[0], General)
    assert len(elements) == 1
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0].metadata.filetype == "message/rfc822"


def test_partition_via_api_with_file_correctly_calls_sdk(
    request: FixtureRequest, expected_call_: list[Any]
):
    partition_mock_ = method_mock(
        request, General, "partition", return_value=FakeResponse(status_code=200)
    )

    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_via_api(
            file=f, metadata_filename=example_doc_path("eml/fake-email.eml")
        )

    # Update the fixture content to match the format passed to partition_via_api
    modified_expected_call = expected_call_[:]
    modified_expected_call[1].partition_parameters.files.content = f

    partition_mock_.assert_called_once_with(
        modified_expected_call[0],
        request=modified_expected_call[1],
        retries=modified_expected_call[2],
    )
    assert isinstance(partition_mock_.call_args_list[0].args[0], General)
    assert len(elements) == 1
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0].metadata.filetype == "message/rfc822"


def test_partition_via_api_warns_with_file_and_filename_and_calls_sdk(
    request: FixtureRequest, expected_call_: list[Any], caplog: pytest.LogCaptureFixture
):
    partition_mock_ = method_mock(
        request, General, "partition", return_value=FakeResponse(status_code=200)
    )

    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        partition_via_api(file=f, file_filename=example_doc_path("eml/fake-email.eml"))

    # Update the fixture content to match the format passed to partition_via_api
    modified_expected_call = expected_call_[:]
    modified_expected_call[1].partition_parameters.files.content = f

    partition_mock_.assert_called_once_with(
        modified_expected_call[0],
        request=modified_expected_call[1],
        retries=modified_expected_call[2],
    )
    assert "WARNING" in caplog.text
    assert "The file_filename kwarg will be deprecated" in caplog.text


def test_partition_via_api_from_file_raises_with_metadata_and_file_and_filename():
    filename = example_doc_path("eml/fake-email.eml")

    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_via_api(file=f, file_filename=filename, metadata_filename=filename)


def test_partition_via_api_from_file_raises_without_filename():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f, pytest.raises(ValueError):
        partition_via_api(file=f)


def test_partition_via_api_raises_with_bad_response(request: FixtureRequest):
    partition_mock_ = method_mock(
        request, General, "partition", return_value=FakeResponse(status_code=500)
    )

    with pytest.raises(ValueError):
        partition_via_api(filename=example_doc_path("eml/fake-email.eml"))
    partition_mock_.assert_called_once()


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_with_no_strategy():
    test_file = example_doc_path("pdf/loremipsum-flat.pdf")
    elements_no_strategy = partition_via_api(
        filename=test_file,
        strategy="auto",
        api_key=get_api_key(),
        # The url has changed since the 06/24 API release while the sdk defaults to the old url
        api_url=API_URL,
        skip_infer_table_types=["pdf"],
    )
    elements_hi_res = partition_via_api(
        filename=test_file,
        strategy="hi_res",
        api_key=get_api_key(),
        # The url has changed since the 06/24 API release while the sdk defaults to the old url
        api_url=API_URL,
        skip_infer_table_types=["pdf"],
    )
    elements_fast_res = partition_via_api(
        filename=test_file,
        strategy="fast",
        api_key=get_api_key(),
        # The url has changed since the 06/24 API release while the sdk defaults to the old url
        api_url=API_URL,
        skip_infer_table_types=["pdf"],
    )

    # confirm that hi_res strategy was not passed as default to partition by comparing outputs
    # elements_hi_res[3].text =
    #     'LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis'
    # while elements_no_strategy[3].text = ']' (as of this writing)
    assert len(elements_no_strategy) == len(elements_hi_res)
    assert len(elements_hi_res) != len(elements_fast_res)

    # NOTE(crag): slightly out scope assertion, but avoid extra API call
    assert elements_hi_res[0].metadata.coordinates is None


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_with_image_hi_res_strategy_includes_coordinates():
    # coordinates not included by default to limit payload size
    elements = partition_via_api(
        filename=example_doc_path("pdf/fake-memo.pdf"),
        strategy="hi_res",
        coordinates="true",
        api_key=get_api_key(),
        api_url=API_URL,
    )

    assert elements[0].metadata.coordinates is not None


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_image_block_extraction():
    elements = partition_via_api(
        filename=example_doc_path("pdf/embedded-images-tables.pdf"),
        strategy="hi_res",
        extract_image_block_types=["image", "table"],
        api_key=get_api_key(),
        # The url has changed since the 06/24 API release while the sdk defaults to the old url
        api_url=API_URL,
    )
    image_elements = [el for el in elements if el.category == ElementType.IMAGE]
    for el in image_elements:
        assert el.metadata.image_base64 is not None
        assert el.metadata.image_mime_type is not None
        image_data = base64.b64decode(el.metadata.image_base64)
        assert isinstance(image_data, bytes)


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_via_api_retries_config():
    elements = partition_via_api(
        filename=example_doc_path("pdf/embedded-images-tables.pdf"),
        strategy="fast",
        api_key=get_api_key(),
        # The url has changed since the 06/24 API release while the sdk defaults to the old url
        api_url=API_URL,
        retries_initial_interval=5,
        retries_max_interval=15,
        retries_max_elapsed_time=100,
        retries_connection_errors=True,
        retries_exponent=1.5,
    )

    assert len(elements) > 0


# Note(austin) - This test is way too noisy against the hosted api
# def test_partition_via_api_invalid_request_data_kwargs():
#     filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "layout-parser-paper-fast.pdf")
#     with pytest.raises(SDKError):
#         partition_via_api(filename=filename, strategy="not_a_strategy")


def test_retries_config_with_parameters_set():
    sdk = Mock()
    retries_config = get_retries_config(
        retries_connection_errors=True,
        retries_exponent=1.75,
        retries_initial_interval=20,
        retries_max_elapsed_time=1000,
        retries_max_interval=100,
        sdk=sdk,
    )

    assert retries_config.retry_connection_errors
    assert retries_config.backoff.exponent == 1.75
    assert retries_config.backoff.initial_interval == 20
    assert retries_config.backoff.max_elapsed_time == 1000
    assert retries_config.backoff.max_interval == 100


def test_retries_config_none_parameters_return_empty_config():
    sdk = Mock()
    retries_config = get_retries_config(
        retries_connection_errors=None,
        retries_exponent=None,
        retries_initial_interval=None,
        retries_max_elapsed_time=None,
        retries_max_interval=None,
        sdk=sdk,
    )

    assert retries_config is None


def test_retry_config_with_empty_sdk_retry_config_returns_default():
    sdk = Mock()
    sdk.sdk_configuration.retry_config = None
    retries_config = get_retries_config(
        retries_connection_errors=True,
        retries_exponent=1.88,
        retries_initial_interval=3000,
        retries_max_elapsed_time=None,
        retries_max_interval=None,
        sdk=sdk,
    )

    assert retries_config.retry_connection_errors
    assert retries_config.backoff.exponent == 1.88
    assert retries_config.backoff.initial_interval == 3000
    assert retries_config.backoff.max_elapsed_time == DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC
    assert retries_config.backoff.max_interval == DEFAULT_RETRIES_MAX_INTERVAL_SEC


def test_retries_config_with_no_parameters_set():
    retry_config = retries.RetryConfig(
        "backoff", retries.BackoffStrategy(3000, 720000, 1.88, 1800000), True
    )
    sdk = Mock()
    sdk.sdk_configuration.retry_config = retry_config
    retries_config = get_retries_config(
        retries_connection_errors=True,
        retries_exponent=None,
        retries_initial_interval=None,
        retries_max_elapsed_time=None,
        retries_max_interval=None,
        sdk=sdk,
    )

    assert retries_config.retry_connection_errors
    assert retries_config.backoff.exponent == 1.88
    assert retries_config.backoff.initial_interval == 3000
    assert retries_config.backoff.max_elapsed_time == 1800000
    assert retries_config.backoff.max_interval == 720000


def test_retries_config_cascade():
    # notice max_interval is set to 0 which is incorrect - so the DEFAULT_RETRIES_MAX_INTERVAL_SEC
    # should be used
    retry_config = retries.RetryConfig(
        "backoff", retries.BackoffStrategy(3000, 0, 1.88, None), True
    )
    sdk = Mock()
    sdk.sdk_configuration.retry_config = retry_config
    retries_config = get_retries_config(
        retries_connection_errors=False,
        retries_exponent=1.75,
        retries_initial_interval=20,
        retries_max_elapsed_time=None,
        retries_max_interval=None,
        sdk=sdk,
    )

    assert not retries_config.retry_connection_errors
    assert retries_config.backoff.exponent == 1.75
    assert retries_config.backoff.initial_interval == 20
    assert retries_config.backoff.max_elapsed_time == DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC
    assert retries_config.backoff.max_interval == DEFAULT_RETRIES_MAX_INTERVAL_SEC


def test_partition_multiple_via_api_with_single_filename(request: FixtureRequest):
    partition_mock_ = method_mock(
        request, requests, "post", return_value=FakeResponse(status_code=200)
    )
    filename = example_doc_path("eml/fake-email.eml")

    elements = partition_multiple_via_api(filenames=[filename])

    partition_mock_.assert_called_once_with(
        "https://api.unstructured.io/general/v0/general",
        headers={"ACCEPT": "application/json", "UNSTRUCTURED-API-KEY": ANY},
        data={},
        files=[("files", (example_doc_path("eml/fake-email.eml"), ANY, None))],
    )
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_from_filenames(request: FixtureRequest):
    partition_mock_ = method_mock(
        request, requests, "post", return_value=FakeMultipleResponse(status_code=200)
    )
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    elements = partition_multiple_via_api(filenames=filenames)

    partition_mock_.assert_called_once_with(
        "https://api.unstructured.io/general/v0/general",
        headers={"ACCEPT": "application/json", "UNSTRUCTURED-API-KEY": ANY},
        data={},
        files=[
            ("files", (example_doc_path("eml/fake-email.eml"), ANY, None)),
            ("files", (example_doc_path("fake.docx"), ANY, None)),
        ],
    )
    assert len(elements) == 2
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_from_files(request: FixtureRequest):
    partition_mock_ = method_mock(
        request, requests, "post", return_value=FakeMultipleResponse(status_code=200)
    )
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        elements = partition_multiple_via_api(
            files=files,
            metadata_filenames=filenames,
        )

    partition_mock_.assert_called_once_with(
        "https://api.unstructured.io/general/v0/general",
        headers={"ACCEPT": "application/json", "UNSTRUCTURED-API-KEY": ANY},
        data={},
        files=[
            ("files", (example_doc_path("eml/fake-email.eml"), ANY, None)),
            ("files", (example_doc_path("fake.docx"), ANY, None)),
        ],
    )
    assert len(elements) == 2
    assert elements[0][0] == NarrativeText("This is a test email to use for unit tests.")
    assert elements[0][0].metadata.filetype == "message/rfc822"


def test_partition_multiple_via_api_warns_with_file_filename(
    caplog: pytest.LogCaptureFixture, request: FixtureRequest
):
    partition_mock_ = method_mock(
        request, requests, "post", return_value=FakeMultipleResponse(status_code=200)
    )
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        partition_multiple_via_api(
            files=files,
            file_filenames=filenames,
        )

    partition_mock_.assert_called_once_with(
        "https://api.unstructured.io/general/v0/general",
        headers={"ACCEPT": "application/json", "UNSTRUCTURED-API-KEY": ANY},
        data={},
        files=[
            ("files", (example_doc_path("eml/fake-email.eml"), ANY, None)),
            ("files", (example_doc_path("fake.docx"), ANY, None)),
        ],
    )
    assert "WARNING" in caplog.text
    assert "The file_filenames kwarg will be deprecated" in caplog.text


def test_partition_multiple_via_api_raises_with_file_and_metadata_filename():
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        with pytest.raises(ValueError):
            partition_multiple_via_api(
                files=files,
                metadata_filenames=filenames,
                file_filenames=filenames,
            )


def test_partition_multiple_via_api_raises_with_bad_response(request: FixtureRequest):
    partition_mock_ = method_mock(
        request, requests, "post", return_value=FakeMultipleResponse(status_code=500)
    )
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with pytest.raises(ValueError):
        partition_multiple_via_api(filenames=filenames)
    partition_mock_.assert_called_once_with(
        "https://api.unstructured.io/general/v0/general",
        headers={"ACCEPT": "application/json", "UNSTRUCTURED-API-KEY": ANY},
        data={},
        files=[
            ("files", (example_doc_path("eml/fake-email.eml"), ANY, None)),
            ("files", (example_doc_path("fake.docx"), ANY, None)),
        ],
    )


def test_partition_multiple_via_api_raises_with_content_types_size_mismatch():
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with pytest.raises(ValueError):
        partition_multiple_via_api(
            filenames=filenames,
            content_types=["text/plain"],
        )


def test_partition_multiple_via_api_from_files_raises_with_size_mismatch():
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
        with pytest.raises(ValueError):
            partition_multiple_via_api(
                files=files,
                metadata_filenames=filenames,
                content_types=["text/plain"],
            )


def test_partition_multiple_via_api_from_files_raises_without_filenames():
    filenames = [example_doc_path("eml/fake-email.eml"), example_doc_path("fake.docx")]

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


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
@pytest.mark.skipif(skip_not_on_main, reason="Skipping test run outside of main branch")
def test_partition_multiple_via_api_valid_request_data_kwargs():
    filenames = [
        example_doc_path("fake-text.txt"),
        example_doc_path("fake-email.txt"),
    ]

    list_of_lists_of_elements = partition_multiple_via_api(
        filenames=filenames,
        strategy="fast",
        api_key=get_api_key(),
        api_url=API_URL,
    )
    # assert there is a list of elements for each file
    assert len(list_of_lists_of_elements) == 2
    assert isinstance(list_of_lists_of_elements[0], list)
    assert isinstance(list_of_lists_of_elements[1], list)


@pytest.mark.skipif(not is_in_ci, reason="Skipping test run outside of CI")
def test_partition_multiple_via_api_invalid_request_data_kwargs():
    filenames = [
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        example_doc_path("img/layout-parser-paper-fast.jpg"),
    ]
    with pytest.raises(ValueError):
        partition_multiple_via_api(
            filenames=filenames,
            strategy="not_a_strategy",
            api_key=get_api_key(),
            # The url has changed since the 06/24 API release while the sdk defaults to the old url
            api_url=API_URL,
        )


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


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code
        # The string representation of partitioned elements is nested in an additional
        # layer in the new unstructured-client:
        #     `elements_from_json(text=response.raw_response.text)`
        self.raw_response = FakeRawResponse()
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return json.loads(self.text)

    @property
    def text(self):
        return MOCK_TEXT


class FakeRawResponse:
    def __init__(self):
        self.text = MOCK_TEXT


class FakeMultipleResponse:
    def __init__(self, status_code: int):
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


@pytest.fixture()
def expected_call_():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        file_bytes = f.read()
    return [
        ANY,
        PartitionRequest(
            partition_parameters=PartitionParameters(
                files=shared.Files(
                    content=file_bytes,
                    file_name=example_doc_path("eml/fake-email.eml"),
                ),
                chunking_strategy=None,
                combine_under_n_chars=None,
                coordinates=False,
                encoding=None,
                extract_image_block_types=None,
                gz_uncompressed_content_type=None,
                hi_res_model_name=None,
                include_orig_elements=None,
                include_page_breaks=False,
                languages=None,
                max_characters=None,
                multipage_sections=True,
                new_after_n_chars=None,
                ocr_languages=None,
                output_format=shared.OutputFormat.APPLICATION_JSON,
                overlap=0,
                overlap_all=False,
                pdf_infer_table_structure=True,
                similarity_threshold=None,
                skip_infer_table_types=None,
                split_pdf_concurrency_level=5,
                split_pdf_page=True,
                starting_page_number=None,
                strategy=shared.Strategy.HI_RES,
                unique_element_ids=False,
                xml_keep_tags=False,
            )
        ),
        None,  # retries kwarg
    ]
