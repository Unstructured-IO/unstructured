import os
import pathlib
from dataclasses import dataclass
from typing import Any, Dict

import pytest

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.connector.sftp import SftpAccessConfig, SimpleSftpConfig
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    FsspecConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "../..", "example-docs")
TEST_DOWNLOAD_DIR = "/tmp"
TEST_OUTPUT_DIR = "/tmp"
TEST_ID = "test"
TEST_FILE_PATH = os.path.join(EXAMPLE_DOCS_DIRECTORY, "book-war-and-peace-1p.txt")


@dataclass
class ExampleConfig(BaseConnectorConfig):
    id: str
    path: str


TEST_CONFIG = ExampleConfig(id=TEST_ID, path=TEST_FILE_PATH)
TEST_SOURCE_URL = "test-source-url"
TEST_VERSION = "1.1.1"
TEST_RECORD_LOCATOR = {"id": "data-source-id"}
TEST_DATE_CREATED = "2021-01-01T00:00:00"
TEST_DATE_MODIFIED = "2021-01-02T00:00:00"
TEST_DATE_PROCESSSED = "2022-12-13T15:44:08"


@dataclass
class ExampleIngestDoc(BaseSingleIngestDoc):
    connector_config: ExampleConfig

    @property
    def filename(self):
        return TEST_FILE_PATH

    @property
    def _output_filename(self):
        return TEST_FILE_PATH + ".json"

    @property
    def source_url(self) -> str:
        return TEST_SOURCE_URL

    @property
    def version(self) -> str:
        return TEST_VERSION

    @property
    def record_locator(self) -> Dict[str, Any]:
        return TEST_RECORD_LOCATOR

    @property
    def date_created(self) -> str:
        return TEST_DATE_CREATED

    @property
    def date_modified(self) -> str:
        return TEST_DATE_MODIFIED

    @property
    def exists(self) -> bool:
        return True

    def cleanup_file(self):
        pass

    def get_file(self):
        pass

    def has_output(self):
        return True

    def write_result(self, result):
        pass


@pytest.fixture()
def partition_test_results():
    # Reusable partition test results, calculated only once
    result = partition(
        filename=str(TEST_FILE_PATH),
        data_source_metadata=DataSourceMetadata(
            url=TEST_SOURCE_URL,
            version=TEST_VERSION,
            record_locator=TEST_RECORD_LOCATOR,
            date_created=TEST_DATE_CREATED,
            date_modified=TEST_DATE_MODIFIED,
            date_processed=TEST_DATE_PROCESSSED,
        ),
    )
    return result


@pytest.fixture()
def partition_file_test_results(partition_test_results):
    # Reusable partition_file test results, calculated only once
    return convert_to_dict(partition_test_results)


def test_partition_file():
    """Validate partition_file returns a list of dictionaries with the expected keys,
    metadatakeys, and data source metadata values."""
    test_ingest_doc = ExampleIngestDoc(
        connector_config=TEST_CONFIG,
        read_config=ReadConfig(download_dir=TEST_DOWNLOAD_DIR),
        processor_config=ProcessorConfig(output_dir=TEST_OUTPUT_DIR),
    )
    test_ingest_doc._date_processed = TEST_DATE_PROCESSSED
    isd_elems_raw = test_ingest_doc.partition_file(partition_config=PartitionConfig())
    isd_elems = convert_to_dict(isd_elems_raw)
    assert len(isd_elems)
    expected_keys = {
        "element_id",
        "text",
        "type",
        "metadata",
    }
    # The document in TEST_FILE_PATH does not have elements with coordinates so
    # partition is not expected to return coordinates metadata.
    expected_metadata_keys = {
        "data_source",
        "filename",
        "file_directory",
        "filetype",
        "languages",
        "last_modified",
    }
    for elem in isd_elems:
        # Parent IDs are non-deterministic - remove them from the test
        elem["metadata"].pop("parent_id", None)

        assert expected_keys == set(elem.keys())
        assert expected_metadata_keys == set(elem["metadata"].keys())
        data_source_metadata = elem["metadata"]["data_source"]
        assert data_source_metadata["url"] == TEST_SOURCE_URL
        assert data_source_metadata["version"] == TEST_VERSION
        assert data_source_metadata["record_locator"] == TEST_RECORD_LOCATOR
        assert data_source_metadata["date_created"] == TEST_DATE_CREATED
        assert data_source_metadata["date_modified"] == TEST_DATE_MODIFIED
        assert data_source_metadata["date_processed"] == TEST_DATE_PROCESSSED


def test_process_file_fields_include_default(mocker, partition_test_results):
    """Validate when metadata_include and metadata_exclude are not set, all fields:
    ("element_id", "text", "type", "metadata") are included"""
    mock_partition = mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    test_ingest_doc = ExampleIngestDoc(
        connector_config=TEST_CONFIG,
        read_config=ReadConfig(download_dir=TEST_DOWNLOAD_DIR),
        processor_config=ProcessorConfig(output_dir=TEST_OUTPUT_DIR),
    )
    isd_elems_raw = test_ingest_doc.partition_file(partition_config=PartitionConfig())
    isd_elems = convert_to_dict(isd_elems_raw)
    assert len(isd_elems)
    assert mock_partition.call_count == 1
    for elem in isd_elems:
        # Parent IDs are non-deterministic - remove them from the test
        elem["metadata"].pop("parent_id", None)

        assert {"element_id", "text", "type", "metadata"} == set(elem.keys())
        data_source_metadata = elem["metadata"]["data_source"]
        assert data_source_metadata["url"] == TEST_SOURCE_URL
        assert data_source_metadata["version"] == TEST_VERSION
        assert data_source_metadata["record_locator"] == TEST_RECORD_LOCATOR
        assert data_source_metadata["date_created"] == TEST_DATE_CREATED
        assert data_source_metadata["date_modified"] == TEST_DATE_MODIFIED
        assert data_source_metadata["date_processed"] == TEST_DATE_PROCESSSED


def test_process_file_metadata_includes_filename_and_filetype(
    mocker,
    partition_test_results,
):
    """Validate when metadata_include is set to "filename,filetype",
    only filename is included in metadata"""
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    partition_config = PartitionConfig(
        metadata_include=["filename", "filetype"],
    )
    test_ingest_doc = ExampleIngestDoc(
        connector_config=TEST_CONFIG,
        read_config=ReadConfig(download_dir=TEST_DOWNLOAD_DIR),
        processor_config=ProcessorConfig(output_dir=TEST_OUTPUT_DIR),
    )
    isd_elems = test_ingest_doc.process_file(partition_config=partition_config)
    assert len(isd_elems)
    for elem in isd_elems:
        # Parent IDs are non-deterministic - remove them from the test
        elem["metadata"].pop("parent_id", None)

        assert set(elem["metadata"].keys()) == {"filename", "filetype"}


def test_process_file_metadata_exclude_filename_pagenum(mocker, partition_test_results):
    """Validate when metadata_exclude is set to "filename,page_number",
    neither filename nor page_number are included in metadata"""
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    partition_config = PartitionConfig(
        metadata_exclude=["filename", "page_number"],
    )
    test_ingest_doc = ExampleIngestDoc(
        connector_config=TEST_CONFIG,
        read_config=ReadConfig(download_dir=TEST_DOWNLOAD_DIR),
        processor_config=ProcessorConfig(
            output_dir=TEST_OUTPUT_DIR,
        ),
    )
    isd_elems = test_ingest_doc.process_file(partition_config=partition_config)
    assert len(isd_elems)
    for elem in isd_elems:
        assert "filename" not in elem["metadata"]
        assert "page_number" not in elem["metadata"]


def test_process_file_flatten_metadata(mocker, partition_test_results):
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    partition_config = PartitionConfig(
        metadata_include=["filename", "file_directory", "filetype"],
        flatten_metadata=True,
    )
    test_ingest_doc = ExampleIngestDoc(
        connector_config=TEST_CONFIG,
        read_config=ReadConfig(download_dir=TEST_DOWNLOAD_DIR),
        processor_config=ProcessorConfig(
            output_dir=TEST_OUTPUT_DIR,
        ),
    )
    isd_elems = test_ingest_doc.process_file(partition_config=partition_config)
    expected_keys = {"element_id", "text", "type", "filename", "file_directory", "filetype"}
    for elem in isd_elems:
        assert expected_keys == set(elem.keys())


def test_post_init_invalid_protocol():
    """Validate that an invalid protocol raises a ValueError"""
    with pytest.raises(ValueError):
        FsspecConfig(remote_url="ftp://example.com/path/to/file.txt")


def test_fsspec_path_extraction_dropbox_root():
    """Validate that the path extraction works for dropbox root"""
    config = FsspecConfig(remote_url="dropbox:// /")
    assert config.protocol == "dropbox"
    assert config.path_without_protocol == " /"
    assert config.dir_path == " "
    assert config.file_path == ""


def test_fsspec_path_extraction_dropbox_subfolder():
    """Validate that the path extraction works for dropbox subfolder"""
    config = FsspecConfig(remote_url="dropbox://path")
    assert config.protocol == "dropbox"
    assert config.path_without_protocol == "path"
    assert config.dir_path == "path"
    assert config.file_path == ""


def test_fsspec_path_extraction_s3_bucket_only():
    """Validate that the path extraction works for s3 bucket without filename"""
    config = FsspecConfig(remote_url="s3://bucket-name")
    assert config.protocol == "s3"
    assert config.path_without_protocol == "bucket-name"
    assert config.dir_path == "bucket-name"
    assert config.file_path == ""


def test_fsspec_path_extraction_s3_valid_path():
    """Validate that the path extraction works for s3 bucket with filename"""
    config = FsspecConfig(remote_url="s3://bucket-name/path/to/file.txt")
    assert config.protocol == "s3"
    assert config.path_without_protocol == "bucket-name/path/to/file.txt"
    assert config.dir_path == "bucket-name"
    assert config.file_path == "path/to/file.txt"


def test_fsspec_path_extraction_s3_invalid_path():
    """Validate that an invalid s3 path (that mimics triple slash for dropbox)
    raises a ValueError"""
    with pytest.raises(ValueError):
        FsspecConfig(remote_url="s3:///bucket-name/path/to")


def test_sftp_path_extraction_post_init_with_extension():
    """Validate that the path extraction works for sftp with file extension"""
    config = SimpleSftpConfig(
        remote_url="sftp://example.com/path/to/file.txt",
        access_config=SftpAccessConfig(username="username", password="password", host="", port=22),
    )
    assert config.file_path == "file.txt"
    assert config.dir_path == "path/to"
    assert config.path_without_protocol == "path/to"
    assert config.access_config.host == "example.com"
    assert config.access_config.port == 22


def test_sftp_path_extraction_without_extension():
    """Validate that the path extraction works for sftp without extension"""
    config = SimpleSftpConfig(
        remote_url="sftp://example.com/path/to/directory",
        access_config=SftpAccessConfig(username="username", password="password", host="", port=22),
    )
    assert config.file_path == ""
    assert config.dir_path == "path/to/directory"
    assert config.path_without_protocol == "path/to/directory"
    assert config.access_config.host == "example.com"
    assert config.access_config.port == 22


def test_sftp_path_extraction_with_port():
    """Validate that the path extraction works for sftp with a non-default port"""
    config = SimpleSftpConfig(
        remote_url="sftp://example.com:47474/path/to/file.txt",
        access_config=SftpAccessConfig(username="username", password="password", host="", port=22),
    )
    assert config.file_path == "file.txt"
    assert config.dir_path == "path/to"
    assert config.path_without_protocol == "path/to"
    assert config.access_config.host == "example.com"
    assert config.access_config.port == 47474
