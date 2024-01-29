import datetime
from unittest.mock import Mock, patch

from unstructured.ingest.connector.sql import SqlDestinationConnector

TEST_DATA_1 = {
    "element_id": "80803034fe04181c163306740700cc54",
    "metadata": {
        "coordinates": {
            "layout_height": 792,
            "layout_width": 612,
            "points": [
                [72.0, 72.69200000000001],
                [72.0, 83.69200000000001],
                [135.8, 83.69200000000001],
                [135.8, 72.69200000000001],
            ],
            "system": "PixelSpace",
        },
        "data_source": {
            "date_created": "2023-10-25 10:05:44.976775",
            "date_modified": "2023-10-25 10:05:44.976775",
            "date_processed": "2023-12-14T17:06:33.074057",
            "permissions_data": [{"mode": 33188}],
            "url": "example-docs/fake-memo.pdf",
        },
        "file_directory": "example-docs",
        "filename": "fake-memo.pdf",
        "filetype": "application/pdf",
        "languages": ["eng"],
        "last_modified": "2023-10-25T10:05:44",
        "page_number": 1,
    },
    "text": "May 5, 2023",
    "type": "UncategorizedText",
    "embeddings": [
        -0.05623878538608551,
        0.008579030632972717,
        0.03698136284947395,
        -0.01745658740401268,
        -0.030465232208371162,
        0.00996527448296547,
    ],
}

TEST_DATA_2 = {
    "metadata": {
        "coordinates": {"points": [1, 2, 3]},
        "links": {"link1": "https://example.com", "link2": "https://example.org"},
        "data_source": {
            "date_created": "2021-01-01T00:00:00",
            "date_modified": "2021-01-02T00:00:00",
            "date_processed": "2022-12-13T15:44:08",
            "version": 1.1,
        },
        "last_modified": "2021-01-03T00:00:00",
        "page_number": 10,
        "regex_metadata": {"pattern": "abc"},
    },
    "embeddings": [0.1, 0.2, 0.3],
}

TEST_DATA_3 = {
    "metadata": {
        "coordinates": {"points": [1, 2, 3]},
        "data_source": {
            "date_created": "2021-01-01T00:00:00",
            "date_modified": "2021-01-02T00:00:00",
            "date_processed": "2022-12-13T15:44:08",
            "version": 1.1,
        },
        "last_modified": "2021-01-03T00:00:00",
        "page_number": 10,
        "link_texts": ["Skip to main content"],
        "link_urls": ["#main-content"],
    },
    "embeddings": [0.1, 0.2, 0.3],
}


def test_conform_dict_1():
    """Validate that the conform_dict method returns the expected output for a real example"""
    # Create a mock instance of the connector class
    connector = SqlDestinationConnector(write_config=Mock(), connector_config=Mock())

    # Mock the uuid.uuid4 function to return a fixed value
    with patch("uuid.uuid4", return_value="mocked_uuid"):
        # Call the conform_dict method
        data_out = TEST_DATA_1.copy()
        connector.conform_dict(data_out)

    # Assert that the result matches the expected output
    assert data_out == {
        "element_id": "80803034fe04181c163306740700cc54",
        "text": "May 5, 2023",
        "type": "UncategorizedText",
        "id": "mocked_uuid",
        "file_directory": "example-docs",
        "filename": "fake-memo.pdf",
        "filetype": "application/pdf",
        "languages": ["eng"],
        "last_modified": datetime.datetime(2023, 10, 25, 10, 5, 44),
        "page_number": "1",
        "date_created": datetime.datetime(2023, 10, 25, 10, 5, 44, 976775),
        "date_modified": datetime.datetime(2023, 10, 25, 10, 5, 44, 976775),
        "date_processed": datetime.datetime(2023, 12, 14, 17, 6, 33, 74057),
        "permissions_data": '[{"mode": 33188}]',
        "url": "example-docs/fake-memo.pdf",
        "layout_height": 792,
        "layout_width": 612,
        "points": "[[72.0, 72.69200000000001], [72.0, 83.69200000000001],"
        " [135.8, 83.69200000000001], [135.8, 72.69200000000001]]",
        "system": "PixelSpace",
        "embeddings": "[-0.05623878538608551, 0.008579030632972717, "
        "0.03698136284947395, -0.01745658740401268, "
        "-0.030465232208371162, 0.00996527448296547]",
    }


def test_conform_dict_2():
    """Validate that the conform_dict method returns the expected output for a simplified example"""
    # Create a mock instance of the connector class
    connector = SqlDestinationConnector(write_config=Mock(), connector_config=Mock())

    # Mock the uuid.uuid4 function to return a fixed value
    with patch("uuid.uuid4", return_value="mocked_uuid"):
        # Call the conform_dict method
        data_out = TEST_DATA_2.copy()
        connector.conform_dict(data_out)

    # Assert that the result matches the expected output
    assert data_out == {
        "embeddings": "[0.1, 0.2, 0.3]",
        "id": "mocked_uuid",
        "links": '{"link1": "https://example.com", "link2": "https://example.org"}',
        "last_modified": datetime.datetime(2021, 1, 3, 0, 0),
        "page_number": "10",
        "regex_metadata": '{"pattern": "abc"}',
        "date_created": datetime.datetime(2021, 1, 1, 0, 0),
        "date_modified": datetime.datetime(2021, 1, 2, 0, 0),
        "date_processed": datetime.datetime(2022, 12, 13, 15, 44, 8),
        "version": "1.1",
        "points": "[1, 2, 3]",
    }


def test_conform_dict_link_texts():
    """Validate that the conform_dict method returns the expected output link_texts"""
    # Create a mock instance of the connector class
    connector = SqlDestinationConnector(write_config=Mock(), connector_config=Mock())

    # Mock the uuid.uuid4 function to return a fixed value
    with patch("uuid.uuid4", return_value="mocked_uuid"):
        # Call the conform_dict method
        data_out = TEST_DATA_3.copy()
        connector.conform_dict(data_out)

    # Assert that the result matches the expected output
    assert data_out == {
        "embeddings": "[0.1, 0.2, 0.3]",
        "id": "mocked_uuid",
        "last_modified": datetime.datetime(2021, 1, 3, 0, 0),
        "link_texts": ["Skip to main content"],
        "link_urls": ["#main-content"],
        "page_number": "10",
        "date_created": datetime.datetime(2021, 1, 1, 0, 0),
        "date_modified": datetime.datetime(2021, 1, 2, 0, 0),
        "date_processed": datetime.datetime(2022, 12, 13, 15, 44, 8),
        "version": "1.1",
        "points": "[1, 2, 3]",
    }
