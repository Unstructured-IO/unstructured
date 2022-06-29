from typing import Dict, List

from unstructured.documents.elements import Text


def convert_to_isd(elements: List[Text]) -> List[Dict[str, str]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, str]] = list()
    for element in elements:
        section = dict(text=element.text, type=element.category)
        isd.append(section)
    return isd
