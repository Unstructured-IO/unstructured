from typing import List, Optional

from unstructured.documents.elements import Element
from unstructured.partition import _partition_via_api


def partition_pdf(
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
        return _partition_pdf_local(filename=filename, file=file, template=template)
    else:
        # NOTE(alan): Remove the "or (template == "checkbox")" after different models are
        # handled by routing
        route = "layout/pdf" if (template is None) or (template == "checkbox") else template
        # NOTE(alan): Remove after different models are handled by routing
        data = {"model": "checkbox"} if (template == "checkbox") else None
        url = f"{url.rstrip('/')}/{route.lstrip('/')}"
        # NOTE(alan): Remove "data=data" after different models are handled by routing
        return _partition_via_api(filename=filename, file=file, url=url, token=token, data=data)


def _partition_pdf_local(
    filename: str = "",
    file: Optional[bytes] = None,
    template: Optional[str] = None,
) -> List[Element]:
    """Partition using package installed locally."""
    try:
        from unstructured_inference.inference.layout import (
            process_data_with_model,
            process_file_with_model,
        )
    except ModuleNotFoundError as e:
        raise Exception(
            "unstructured_inference module not found... try running pip install "
            "unstructured[local-inference] if you installed the unstructured library as a package. "
            "If you cloned the unstructured repository, try running make install-local-inference "
            "from the root directory of the repository."
        ) from e
    except ImportError as e:
        raise Exception(
            "There was a problem importing unstructured_inference module - it may not be installed "
            "correctly... try running pip install unstructured[local-inference] if you installed "
            "the unstructured library as a package. If you cloned the unstructured repository, try "
            "running make install-local-inference from the root directory of the repository."
        ) from e

    layout = (
        process_file_with_model(filename, template)
        if file is None
        else process_data_with_model(file, template)
    )
    return [element for page in layout.pages for element in page.elements]
