import warnings
from typing import List, Optional

from unstructured.documents.elements import Element
from unstructured.partition import _partition_via_api
from unstructured.partition.common import (
    add_element_metadata,
    document_to_element_list,
)


def partition_pdf(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = None,
    template: Optional[str] = None,
    token: Optional[str] = None,
    include_page_breaks: bool = False,
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
    if template is None:
        template = "layout/pdf"
    return partition_pdf_or_image(
        filename=filename,
        file=file,
        url=url,
        template=template,
        token=token,
        include_page_breaks=include_page_breaks,
    )


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = "https://ml.unstructured.io/",
    template: str = "layout/pdf",
    token: Optional[str] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
) -> List[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    if url is None:
        # TODO(alan): Extract information about the filetype to be processed from the template
        # route. Decoding the routing should probably be handled by a single function designed for
        # that task so as routing design changes, those changes are implemented in a single
        # function.
        route_args = template.strip("/").split("/")
        is_image = route_args[-1] == "image"
        out_template: Optional[str] = template
        if route_args[0] == "layout":
            out_template = None

        # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            layout_elements = _partition_pdf_or_image_local(
                filename=filename,
                file=file,
                template=out_template,
                is_image=is_image,
                include_page_breaks=True,
            )
    else:
        # NOTE(alan): Remove these lines after different models are handled by routing
        if template == "checkbox":
            template = "layout/pdf"
        # NOTE(alan): Remove after different models are handled by routing
        data = {"model": "checkbox"} if (template == "checkbox") else None
        url = f"{url.rstrip('/')}/{template.lstrip('/')}"
        # NOTE(alan): Remove "data=data" after different models are handled by routing
        layout_elements = _partition_via_api(
            filename=filename,
            file=file,
            url=url,
            token=token,
            data=data,
            include_page_breaks=True,
        )

    return add_element_metadata(
        layout_elements,
        include_page_breaks=include_page_breaks,
        filename=filename,
    )


def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[bytes] = None,
    template: Optional[str] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
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
            "from the root directory of the repository.",
        ) from e
    except ImportError as e:
        raise Exception(
            "There was a problem importing unstructured_inference module - it may not be installed "
            "correctly... try running pip install unstructured[local-inference] if you installed "
            "the unstructured library as a package. If you cloned the unstructured repository, try "
            "running make install-local-inference from the root directory of the repository.",
        ) from e

    layout = (
        process_file_with_model(filename, template, is_image=is_image)
        if file is None
        else process_data_with_model(file, template, is_image=is_image)
    )

    return document_to_element_list(layout, include_page_breaks=include_page_breaks)
