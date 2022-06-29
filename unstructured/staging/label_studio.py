from typing import Dict, List

from unstructured.documents.elements import Text


LABEL_STUDIO_TYPE = List[Dict[str, Dict[str, str]]]


def stage_for_label_studio(elements: List[Text]) -> LABEL_STUDIO_TYPE:
    """Converts the document to the format required for upload to LabelStudio.
    ref: https://labelstud.io/guide/tasks.html#Example-JSON-format"""
    label_studio_data: LABEL_STUDIO_TYPE = list()
    for element in elements:
        data: Dict[str, str] = dict()
        data["my_text"] = element.text
        if isinstance(element.id, str):
            data["ref_id"] = element.id
        label_studio_data.append({"data": data})
    return label_studio_data
