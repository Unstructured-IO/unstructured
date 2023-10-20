import hashlib
from collections import defaultdict

from unstructured_inference.constants import Source


def clean_pdfminer_inner_elements(document):
    """Clean pdfminer elements from inside tables and stores them in extra_info dictionary
    with the table id as key"""
    extra_info = defaultdict(list)
    for page in document.pages:
        tables = [e for e in page.elements if e.type == "Table"]
        for element in page.elements:
            if element.source == Source.PDFMINER:
                element_inside_table = [element.bbox.is_in(t.bbox) for t in tables]
                if sum(element_inside_table) == 1:
                    parent_table_index = element_inside_table.index(True)
                    parent_table = tables[parent_table_index]
                    # Note(Benjamin): is this a good way to guess the id?
                    future_id = hashlib.sha256(parent_table.text.encode()).hexdigest()[:32]
                    extra_info[future_id].append(element)
                    page.elements.remove(element)

    return document, extra_info
