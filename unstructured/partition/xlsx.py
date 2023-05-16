from typing import List

import pandas as pd

from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.partition.html import partition_html


def partition_xlsx(filename: str) -> List[Element]:
    sheets = pd.read_excel(filename, sheet_name=None)

    elements: List[Element] = []
    page_number = 0
    for sheet_name, table in sheets.items():
        page_number += 1
        html_text = table.to_html(index=False).replace("NaN", "")
        html_elements = partition_html(text=html_text, include_metadata=False)
        text = "\n\n".join([str(element) for element in html_elements])

        metadata = ElementMetadata(
            text_as_html=html_text,
            page_number=page_number,
            filename=filename,
        )
        table = Table(text=text, metadata=metadata)
        elements.append(table)

    return elements
