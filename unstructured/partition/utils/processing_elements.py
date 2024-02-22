from collections import defaultdict
from typing import TYPE_CHECKING

from unstructured.partition.utils.constants import Source

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout


def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables and stores them in extra_info dictionary
    with the table id as key"""
    defaultdict(list)
    for page in document.pages:
        tables = [e for e in page.elements if e.type == "Table"]
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER:
                continue
            element_inside_table = [element.bbox.is_in(t.bbox, error_margin=15) for t in tables]
            if sum(element_inside_table) == 1:
                page.elements[i] = None
        page.elements = [e for e in page.elements if e]

    return document
