import os

import pandas as pd

import unstructured.file_utils.exploration as exploration


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
