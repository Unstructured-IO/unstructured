import contextlib
import json
from typing import (
    IO,
    List,
    Optional,
)

import requests

from unstructured.documents.elements import Element
from unstructured.partition.common import exactly_one
from unstructured.partition.json import partition_json


def partition_via_api(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
    file_filename: Optional[str] = None,
    strategy: str = "hi_res",
    api_url: str = "https://api.unstructured.io/general/v0/general",
    api_key: str = "",
) -> List[Element]:
    """Partitions a document using the Unstructured REST API. This is equivalent to
    running the document through partition.

    See https://api.unstructured.io/general/docs for the hosted API documentation or
    https://github.com/Unstructured-IO/unstructured-api for instructions on how to run
    the API locally as a container.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    content_type
        A string defining the file content in MIME type
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    file_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    strategy
        The strategy to use for partitioning the PDF. Uses a layout detection model if set
        to 'hi_res', otherwise partition_pdf simply extracts the text from the document
        and processes it.
    api_url
        The URL for the Unstructured API. Defaults to the hosted Unstructured API.
    api_key
        The API key to pass to the Unstructured API.
    """
    exactly_one(filename=filename, file=file)

    headers = {
        "ACCEPT": "application/json",
        "UNSTRUCTURED-API-KEY": api_key,
    }

    data = {
        "strategy": strategy,
    }

    if filename is not None:
        with open(filename, "rb") as f:
            files = [
                ("files", (filename, f, content_type)),
            ]
            response = requests.post(
                api_url,
                headers=headers,
                data=data,
                files=files,  # type: ignore
            )
    elif file is not None:
        _filename = file_filename or ""
        files = [
            ("files", (_filename, file, content_type)),  # type: ignore
        ]
        response = requests.post(api_url, headers=headers, data=data, files=files)  # type: ignore

    if response.status_code == 200:
        return partition_json(text=response.text)
    else:
        raise ValueError(
            f"Receive unexpected status code {response.status_code} from the API.",
        )


def partition_multiple_via_api(
    filenames: Optional[List[str]] = None,
    content_types: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    file_filenames: Optional[List[str]] = None,
    strategy: str = "hi_res",
    api_url: str = "https://api.unstructured.io/general/v0/general",
    api_key: str = "",
) -> List[List[Element]]:
    """Partitions multiple document using the Unstructured REST API by batching
    the documents into a single HTTP request.

    See https://api.unstructured.io/general/docs for the hosted API documentation or
    https://github.com/Unstructured-IO/unstructured-api for instructions on how to run
    the API locally as a container.

    Parameters
    ----------
    filename
        A list of strings defining the target filename paths.
    content_types
        A list of strings defining the file contents in MIME types.
    files
        A list of file-like object using "rb" mode --> open(filename, "rb").
    file_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    strategy
        The strategy to use for partitioning the PDF. Uses a layout detection model if set
        to 'hi_res', otherwise partition_pdf simply extracts the text from the document
        and processes it.
    api_url
        The URL for the Unstructured API. Defaults to the hosted Unstructured API.
    api_key
        The API key to pass to the Unstructured API.
    """
    headers = {
        "ACCEPT": "application/json",
        "UNSTRUCTURED-API-KEY": api_key,
    }

    data = {
        "strategy": strategy,
    }

    if filenames is not None:
        if content_types and len(content_types) != len(filenames):
            raise ValueError("content_types and filenames must have the same length.")

        with contextlib.ExitStack() as stack:
            files = [stack.enter_context(open(f, "rb")) for f in filenames]  # type: ignore

            _files = []
            for i, file in enumerate(files):
                filename = filenames[i]
                content_type = content_types[i] if content_types is not None else None
                _files.append(("files", (filename, file, content_type)))

            response = requests.post(
                api_url,
                headers=headers,
                data=data,
                files=_files,  # type: ignore
            )

    elif files is not None:
        if content_types and len(content_types) != len(files):
            raise ValueError("content_types and files must have the same length.")

        if not file_filenames:
            raise ValueError("file_filenames must be specified if files are passed")
        elif len(file_filenames) != len(files):
            raise ValueError("file_filenames and files must have the same length.")

        _files = []
        for i, _file in enumerate(files):  # type: ignore
            content_type = content_types[i] if content_types is not None else None
            filename = file_filenames[i]
            _files.append(("files", (filename, _file, content_type)))

        response = requests.post(api_url, headers=headers, data=data, files=_files)  # type: ignore

    if response.status_code == 200:
        documents = []
        for document in response.json():
            documents.append(partition_json(text=json.dumps(document)))
        return documents
    else:
        raise ValueError(
            f"Receive unexpected status code {response.status_code} from the API.",
        )
