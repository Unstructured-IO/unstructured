import os
from typing import Any, Dict, List

import pandas as pd

from unstructured.file_utils.filetype import detect_filetype


def get_directory_file_info(directory: str) -> pd.DataFrame:
    """Recursively walks a directory and extracts key file information to support initial
    exploration of text data sets. Returns a pandas DataFrame."""
    data: Dict[str, List[Any]] = {
        "filename": [],
        "path": [],
        "filesize": [],
        "extension": [],
        "filetype": [],
    }
    for path, _, files in os.walk(directory):
        for filename_no_path in files:
            filename = os.path.join(path, filename_no_path)
            _, extension = os.path.splitext(filename)
            filesize = os.path.getsize(filename)
            filetype = detect_filetype(filename)

            data["filename"].append(filename_no_path)
            data["path"].append(path)
            data["extension"].append(extension)
            data["filesize"].append(filesize)
            data["filetype"].append(filetype)

    return pd.DataFrame(data)
