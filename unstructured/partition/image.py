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
    return partition_pdf_or_image(
        filename=filename, file=file, url=url, template=template, token=token, is_image=True
    )
