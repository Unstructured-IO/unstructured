import os
import pathlib

import pandas as pd
import pytest

from unstructured.file_utils import exploration
from unstructured.file_utils.model import FileType

DIRECTORY = pathlib.Path(__file__).parent.resolve()


is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_get_directory_file_info(tmpdir):
    file_info_test = os.path.join(tmpdir, "file_info_test")
    if not os.path.exists(file_info_test):
        os.mkdir(file_info_test)

    directory1 = os.path.join(file_info_test, "directory1")
    if not os.path.exists(directory1):
        os.mkdir(directory1)

    filename1 = os.path.join(directory1, "filename1.txt")
    with open(filename1, "w") as f:
        f.write("hello there!")

    directory2 = os.path.join(file_info_test, "directory2")
    if not os.path.exists(directory2):
        os.mkdir(directory2)

    filename2 = os.path.join(directory2, "filename2.txt")
    with open(filename2, "w") as f:
        f.write("hello there!")

    file_info = exploration.get_directory_file_info(file_info_test)
    assert isinstance(file_info, pd.DataFrame)
    assert set(file_info["filename"].to_list()) == {"filename1.txt", "filename2.txt"}

    means = file_info.groupby("filetype").mean(numeric_only=True)
    assert means.columns.to_list() == ["filesize"]


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_get_file_info(tmpdir):
    file_info_test = os.path.join(tmpdir, "file_info_test")
    if not os.path.exists(file_info_test):
        os.mkdir(file_info_test)

    directory1 = os.path.join(file_info_test, "directory1")
    if not os.path.exists(directory1):
        os.mkdir(directory1)

    filename1 = os.path.join(directory1, "filename1.txt")
    with open(filename1, "w") as f:
        f.write("hello there!")

    directory2 = os.path.join(file_info_test, "directory2")
    if not os.path.exists(directory2):
        os.mkdir(directory2)

    filename2 = os.path.join(directory2, "filename2.txt")
    with open(filename2, "w") as f:
        f.write("hello there!")

    file_info = exploration.get_file_info([filename1, filename2])
    assert isinstance(file_info, pd.DataFrame)
    assert set(file_info["filename"].to_list()) == {"filename1.txt", "filename2.txt"}

    means = file_info.groupby("filetype").mean(numeric_only=True)
    assert means.columns.to_list() == ["filesize"]


def test_get_file_info_from_file_contents():
    file_contents_filename = os.path.join(DIRECTORY, "test-file-contents.txt")
    with open(file_contents_filename) as f:
        file_contents = [f.read()]

    file_info = exploration.get_file_info_from_file_contents(
        file_contents=file_contents,
        filenames=["test.eml"],
    )
    assert file_info.filetype[0] == FileType.EML


def test_get_file_info_from_file_contents_raises_if_lists_no_equal():
    file_contents_filename = os.path.join(DIRECTORY, "test-file-contents.txt")
    with open(file_contents_filename) as f:
        file_contents = [f.read()]

    with pytest.raises(ValueError):
        exploration.get_file_info_from_file_contents(
            file_contents=file_contents,
            filenames=["test.eml", "test2.eml"],
        )
