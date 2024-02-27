from datetime import datetime
from unittest.mock import MagicMock

import pytest

from unstructured.ingest.connector.sharepoint import SharepointIngestDoc
from unstructured.ingest.interfaces import ProcessorConfig, ReadConfig


@pytest.mark.parametrize(
    ("time_created", "time_last_modified", "expected_created", "expected_modified"),
    [
        (
            "2023-06-16T05:05:05+00:00",
            datetime(2023, 6, 16, 5, 5, 5),
            "2023-06-16T05:05:05+00:00",
            "2023-06-16T05:05:05",
        ),
        ("2023-06-16 05:05:05", "2023-06-16", "2023-06-16T05:05:05", "2023-06-16T00:00:00"),
        # Add more pairs of input strings and their expected ISO format results here
    ],
)
def test_datetime_handling_in_update_source_metadata(
    mocker, time_created, time_last_modified, expected_created, expected_modified
):
    """Test the handling of various datetime formats in update_source_metadata."""
    # Create a mock SharePoint response directly in the test
    mock_sharepoint_response = mocker.MagicMock()
    mock_sharepoint_response.time_created = time_created
    mock_sharepoint_response.time_last_modified = time_last_modified

    # Patch the SharePoint interaction methods to use the mock response
    mocker.patch(
        "unstructured.ingest.connector.sharepoint.SharepointIngestDoc._fetch_file",
        return_value=mock_sharepoint_response,
    )
    mocker.patch(
        "unstructured.ingest.connector.sharepoint.SharepointIngestDoc._fetch_page",
        return_value=None,
    )

    # Instantiate your document with dummy data
    ingest_doc = SharepointIngestDoc(
        connector_config=MagicMock(),
        site_url="dummy_url",
        server_path="dummy_path",
        is_page=False,
        file_path="dummy_path.html",
        processor_config=ProcessorConfig(),
        read_config=ReadConfig(),
    )

    # Execute the method under test
    ingest_doc.update_source_metadata()

    # Assertions to verify the datetime handling against expected results
    assert ingest_doc.source_metadata is not None
    assert ingest_doc.source_metadata.date_created.startswith(expected_created)
    assert ingest_doc.source_metadata.date_modified.startswith(expected_modified)
