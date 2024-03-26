from collections import defaultdict
from typing import TYPE_CHECKING

from unstructured.documents.elements import ElementType
from unstructured.partition.utils.constants import Source
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout


@requires_dependencies("unstructured_inference")
def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables and stores them in extra_info dictionary
    with the table id as key"""

    from unstructured_inference.config import inference_config

    defaultdict(list)
    for page in document.pages:
        tables = [e for e in page.elements if e.type == ElementType.TABLE]
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER:
                continue
            subregion_threshold = inference_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD
            element_inside_table = [
                element.bbox.is_almost_subregion_of(t.bbox, subregion_threshold) for t in tables
            ]
            if sum(element_inside_table) == 1:
                page.elements[i] = None
        page.elements = [e for e in page.elements if e]

    return document
