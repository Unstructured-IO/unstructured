from typing import BinaryIO, List, Mapping, Optional, Tuple, Union
from urllib.parse import urlsplit

import requests  # type: ignore

from unstructured.documents.elements import Element


def _partition_via_api(
    filename: str = "",
    file: Optional[bytes] = None,
    url: str = "https://ml.unstructured.io/layout/pdf",
    token: Optional[str] = None,
    data: Optional[dict] = None,  # NOTE(alan): Remove after different models are handled by routing
    include_page_breaks: bool = False,
) -> List[Element]:
    """Use API for partitioning."""
    if not filename and not file:
        raise FileNotFoundError("No filename nor file were specified")

    split_url = urlsplit(url)
    healthcheck_url = f"{split_url.scheme}://{split_url.netloc}/healthcheck"
    healthcheck_response = requests.models.Response()
    if not token:
        healthcheck_response = requests.get(url=healthcheck_url)

    if healthcheck_response.status_code != 200:
        raise ValueError("endpoint api healthcheck has failed!")

    file_: Mapping[str, Tuple[str, Union[BinaryIO, bytes]]] = {
        "file": (
            filename,
            file if file else open(filename, "rb"),  # noqa: SIM115
        ),
    }
    response = requests.post(
        url=url,
        headers={"Authorization": f"Bearer {token}" if token else ""},
        files=file_,
        data=data,  # NOTE(alan): Remove after unstructured API is using routing
    )

    if response.status_code == 200:
        pages = response.json()["pages"]
        num_pages = len(pages)
        elements = []
        for i, page in enumerate(pages):
            for element in page["elements"]:
                elements.append(element)
            if include_page_breaks and i < num_pages - 1:
                elements.append({"type": "PageBreak"})

        return elements

    else:
        raise ValueError(f"response status code = {response.status_code}")
