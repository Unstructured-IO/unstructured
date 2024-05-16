from dataclasses import dataclass
from pathlib import Path

import pytest

from unstructured.ingest.connector.fsspec.dropbox import (
    DropboxIngestDoc,
)
from unstructured.ingest.connector.fsspec.fsspec import (
    FsspecIngestDoc,
)
from unstructured.ingest.connector.fsspec.sftp import SftpAccessConfig, SimpleSftpConfig
from unstructured.ingest.interfaces import (
    FsspecConfig,
)


@dataclass
class FakeConfigDropboxRoot:
    output_dir = "/fakeuser/fake_output"
    dir_path = " "
    download_dir = "/fakeuser/fake_download"
    path_without_protocol = " "


@dataclass
class FakeConfigFolder:
    output_dir = "/fakeuser/fake_output"
    dir_path = "fake_folder"
    download_dir = "/fakeuser/fake_download"
    path_without_protocol = "fake_folder"


def test_dropbox_root_succeeds():
    """
    Test that path joining method works for Dropbox root folder.
    Note slash in front of remote_file_path.
    """
    dbox = DropboxIngestDoc(
        connector_config=FakeConfigDropboxRoot,
        read_config=FakeConfigDropboxRoot,
        processor_config=FakeConfigDropboxRoot,
        remote_file_path="/fake_file.txt",
    )
    output_filename = dbox._output_filename
    download_filename = dbox._tmp_download_file()

    assert output_filename == Path("/fakeuser/fake_output/fake_file.txt.json")
    assert download_filename == Path("/fakeuser/fake_download/fake_file.txt")


def test_dropbox_root_succeeds2():
    """
    Test that path joining method works for Dropbox root folder.
    Note lack of slash in front of remote_file_path. This still works.
    """
    dbox = DropboxIngestDoc(
        connector_config=FakeConfigDropboxRoot,
        read_config=FakeConfigDropboxRoot,
        processor_config=FakeConfigDropboxRoot,
        remote_file_path="fake_file.txt",
    )
    output_filename = dbox._output_filename
    download_filename = dbox._tmp_download_file()

    assert output_filename == Path("/fakeuser/fake_output/fake_file.txt.json")
    assert download_filename == Path("/fakeuser/fake_download/fake_file.txt")


def test_dropbox_folder_succeeds():
    """
    Test that path joining method works for Dropbox root folder.
    Note no slash in front of remote_file_path.
    """
    dbox = DropboxIngestDoc(
        connector_config=FakeConfigFolder,
        read_config=FakeConfigFolder,
        processor_config=FakeConfigFolder,
        remote_file_path="fake_file2.txt",
    )
    output_filename = dbox._output_filename
    download_filename = dbox._tmp_download_file()

    assert output_filename == Path("/fakeuser/fake_output/fake_file2.txt.json")
    assert download_filename == Path("/fakeuser/fake_download/fake_file2.txt")


def test_dropbox_folder_fails():
    """Test that path joining method gives WRONG path. Note slash in front of remote_file_path.
    Path joining is sensitive. Note that the path is MISSING the folders."""
    dbox = DropboxIngestDoc(
        connector_config=FakeConfigFolder,
        read_config=FakeConfigFolder,
        processor_config=FakeConfigFolder,
        remote_file_path="/fake_file2.txt",
    )
    output_filename = dbox._output_filename
    download_filename = dbox._tmp_download_file()

    assert output_filename == Path("/fake_file2.txt.json")
    assert download_filename == Path("/fake_file2.txt")


def test_fsspec_folder_succeeds():
    """
    Test that path joining method works for root folder.
    Note no slash in front of remote_file_path.
    """
    dbox = FsspecIngestDoc(
        connector_config=FakeConfigFolder,
        read_config=FakeConfigFolder,
        processor_config=FakeConfigFolder,
        remote_file_path="fake_file2.txt",
    )
    output_filename = dbox._output_filename
    download_filename = dbox._tmp_download_file()

    assert output_filename == Path("/fakeuser/fake_output/fake_file2.txt.json")
    assert download_filename == Path("/fakeuser/fake_download/fake_file2.txt")


def test_fsspec_folder_fails():
    """Test that path joining method gives WRONG path. Note slash in front of remote_file_path.
    Path joining is sensitive. Note that the path is MISSING the folders."""
    fstest = FsspecIngestDoc(
        connector_config=FakeConfigFolder,
        read_config=FakeConfigFolder,
        processor_config=FakeConfigFolder,
        remote_file_path="/fake_file2.txt",
    )
    output_filename = fstest._output_filename
    download_filename = fstest._tmp_download_file()

    assert output_filename == Path("/fake_file2.txt.json")
    assert download_filename == Path("/fake_file2.txt")


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
