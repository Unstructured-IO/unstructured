from unittest.mock import MagicMock, patch

from fsspec import AbstractFileSystem

from unstructured.ingest.connector.fsspec.fsspec import FsspecIngestDoc, SimpleFsspecConfig
from unstructured.ingest.interfaces import ProcessorConfig, ReadConfig


@patch("fsspec.get_filesystem_class")
def test_version_is_string(mock_get_filesystem_class):
    """
    Test that the version is a string even when the filesystem checksum is an integer.
    """
    mock_fs = MagicMock(spec=AbstractFileSystem)
    mock_fs.checksum.return_value = 1234567890
    mock_fs.info.return_value = {"etag": ""}
    mock_get_filesystem_class.return_value = lambda **kwargs: mock_fs
    config = SimpleFsspecConfig("s3://my-bucket", access_config={})
    doc = FsspecIngestDoc(
        processor_config=ProcessorConfig(),
        read_config=ReadConfig(),
        connector_config=config,
        remote_file_path="test.txt",
    )
    assert isinstance(doc.source_metadata.version, str)
