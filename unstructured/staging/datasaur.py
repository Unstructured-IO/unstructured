from typing import Dict, List, Any
from unstructured.documents.elements import Text


def stage_for_datasaur(elements: List[Text]) -> List[Dict[str, Any]]:
    """Convert a list of elements into a list of dictionaries for use in Datasaur"""
    result: List[Dict[str, Any]] = list()
    for item in elements:
        data = dict(text=item.text, entities=[])
        result.append(data)

    return result
