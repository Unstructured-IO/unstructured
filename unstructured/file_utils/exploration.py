import base64
import io
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from unstructured.file_utils.filetype import detect_filetype


def get_directory_file_info(directory: str) -> pd.DataFrame:
    """Recursively walks a directory and extracts key file information to support initial
    exploration of text data sets. Returns a pandas DataFrame."""
    filenames: List[str] = []
    for path, _, files in os.walk(directory):
        for filename_no_path in files:
            filenames.append(os.path.join(path, filename_no_path))
    return get_file_info(filenames)


def get_file_info(filenames: List[str]) -> pd.DataFrame:
    """Returns a pandas DataFrame summarizing the filetypes for a list of files."""
    data: Dict[str, List[Any]] = {
        "filename": [],
        "path": [],
        "filesize": [],
        "extension": [],
        "filetype": [],
    }

    for filename in filenames:
        path, filename_no_path = os.path.split(os.path.abspath(filename))
        _, extension = os.path.splitext(filename)
        filesize = os.path.getsize(filename)
        filetype = detect_filetype(filename)

        data["filename"].append(filename_no_path)
        data["path"].append(path)
        data["extension"].append(extension)
        data["filesize"].append(filesize)
        data["filetype"].append(filetype)

    return pd.DataFrame(data)


def get_file_info_from_file_contents(
    file_contents: List[str],
    filenames: Optional[List[str]] = None,
) -> pd.DataFrame:
    data: Dict[str, List[Any]] = {
        "filesize": [],
        "filetype": [],
    }

    if filenames:
        if len(filenames) != len(file_contents):
            raise ValueError(
                f"There are {len(filenames)} filenames and {len(file_contents)} "
                "file_contents. Both inputs must be the same length.",
            )
        data["filename"] = []

    for i, file_content in enumerate(file_contents):
        content_string = file_content.split(",")[-1]
        content_bytes = base64.b64decode(content_string)
        f = io.BytesIO(content_bytes)
        filetype = detect_filetype(file=f)
        f.seek(0, os.SEEK_END)
        filesize = f.tell()

        data["filesize"].append(filesize)
        data["filetype"].append(filetype)
        if filenames:
            data["filename"].append(filenames[i])

    return pd.DataFrame(data)
