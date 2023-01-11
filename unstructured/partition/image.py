from typing import List, Optional

from unstructured.documents.elements import Element
from unstructured.partition import _partition_via_api


def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = "https://ml.unstructured.io/",
    template: Optional[str] = None,
    token: Optional[str] = None,
) -> List[Element]:
    """Parses a pdf document into a list of interpreted elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    template
        A string defining the model to be used. Default None uses default model ("layout/pdf" url
        if using the API).
    url
        A string endpoint to self-host an inference API, if desired. If None, local inference will
        be used.
    token
        A string defining the authentication token for a self-host url, if applicable.
    """
    if url is None:
        return _partition_image_local(filename=filename, file=file, template=template)
    else:
        # NOTE(alan): Remove the "or (template == "checkbox")" after different models are
        # handled by routing
        route = "layout/pdf" if (template is None) or (template == "checkbox") else template
        # NOTE(alan): Remove after different models are handled by routing
        data = {"model": "checkbox"} if (template == "checkbox") else None
        url = f"{url.rstrip('/')}/{route.lstrip('/')}"
        # NOTE(alan): Remove "data=data" after different models are handled by routing
        return _partition_via_api(filename=filename, file=file, url=url, token=token, data=data)


def _partition_image_local(filename=None, file=None, template=None):
    pass
