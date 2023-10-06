from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.connector.dropbox import (
    DropboxIngestDoc,
)
from unstructured.ingest.connector.fsspec import (
    FsspecIngestDoc,
)


@dataclass
class FakeConfigDropboxRoot:
    output_dir = "/fakeuser/fake_output"
    dir_path = " "
    download_dir = "/fakeuser/fake_download"


@dataclass
class FakeConfigFolder:
    output_dir = "/fakeuser/fake_output"
    dir_path = "fake_folder"
    download_dir = "/fakeuser/fake_download"


class DropboxIngestTestDoc(DropboxIngestDoc):
    def __post_init__(self):
        return None


class FsspecIngestTestDoc(FsspecIngestDoc):
    def __post_init__(self):
        return None


def test_dropbox_root_succeeds():
    """
    Test that path joining method works for Dropbox root folder.
    Note slash in front of remote_file_path.
    """
    dbox = DropboxIngestTestDoc(
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
    dbox = DropboxIngestTestDoc(
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
    dbox = DropboxIngestTestDoc(
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
    dbox = DropboxIngestTestDoc(
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
    dbox = FsspecIngestTestDoc(
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
    fstest = FsspecIngestTestDoc(
        connector_config=FakeConfigFolder,
        read_config=FakeConfigFolder,
        processor_config=FakeConfigFolder,
        remote_file_path="/fake_file2.txt",
    )
    output_filename = fstest._output_filename
    download_filename = fstest._tmp_download_file()

    assert output_filename == Path("/fake_file2.txt.json")
    assert download_filename == Path("/fake_file2.txt")
