from typing import List, Optional

from unstructured.documents.elements import Element
from unstructured.partition.pdf import partition_pdf_or_image


def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = "https://ml.unstructured.io/",
    template: Optional[str] = None,
    token: Optional[str] = None,
) -> List[Element]:
    """Parses an image into a list of interpreted elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    template
        A string defining the model to be used. Default None uses default model ("layout/image" url
        if using the API).
    url
        A string endpoint to self-host an inference API, if desired. If None, local inference will
        be used.
    token
        A string defining the authentication token for a self-host url, if applicable.
    """
    if template is None:
        template = "layout/image"
    return partition_pdf_or_image(
        filename=filename, file=file, url=url, template=template, token=token
    )
