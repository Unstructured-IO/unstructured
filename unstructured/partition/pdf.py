import requests  # type: ignore

import sys

if sys.version_info < (3, 8):
    from typing_extensions import (
        List,
        Optional,
        Union,
        Tuple,
        Mapping,
        BinaryIO,
    )  # pragma: no cover
else:
    from typing import List, Optional, Union, Tuple, Mapping, BinaryIO  # pragma: no cover

from unstructured.documents.elements import Element


def partition_pdf(
    filename: str = "",
    file: Optional[bytes] = None,
    url: str = "https://ml.unstructured.io/",
    template: Optional[str] = "base-model",
    token: Optional[str] = None,
) -> List[Element]:
    """Calls the document parsing API.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    template
        A string defining the model to be used. Default "base-model" makes reference to layout/pdf.
    url
        A string endpoint to self-host an inference API, if desired.
    token
        A string defining the authentication token for a self-host url.
    """
    if not filename and not file:
        raise FileNotFoundError("No filename nor file were specified")

    healthcheck_response = requests.models.Response()
    if not token:
        healthcheck_response = requests.get(url=f"{url}healthcheck")

    if healthcheck_response.status_code != 200:
        raise ValueError("endpoint api healthcheck has failed!")

    url = f"{url}layout/pdf" if template == "base-model" else f"{url}/{template}"

    file_: Mapping[str, Tuple[str, Union[BinaryIO, bytes]]] = {
        "file": (
            filename,
            file if file else open(filename, "rb"),
        )
    }
    response = requests.post(
        url=url,
        headers={"Authorization": f"Bearer {token}" if token else ""},
        files=file_,
    )

    if response.status_code == 200:
        pages = response.json()["pages"]
        return [element for page in pages for element in page["elements"]]
    else:
        raise ValueError(f"response status code = {response.status_code}")
