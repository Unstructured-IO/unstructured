import os
from typing import Any, Dict, List

import pandas as pd

from unstructured.file_utils.filetype import detect_filetype


def files_to_dataframe(directory: str) -> pd.DataFrame:
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
