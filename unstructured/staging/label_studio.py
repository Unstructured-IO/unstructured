from typing import Dict, List

from unstructured.documents.elements import Text


LABEL_STUDIO_TYPE = List[Dict[str, Dict[str, str]]]


def stage_for_label_studio(
    elements: List[Text], text_field: str = "text", id_field: str = "ref_id"
) -> LABEL_STUDIO_TYPE:
    """Converts the document to the format required for upload to LabelStudio.
    ref: https://labelstud.io/guide/tasks.html***REMOVED***Example-JSON-format"""
    label_studio_data: LABEL_STUDIO_TYPE = list()
    for element in elements:
        data: Dict[str, str] = dict()
        data[text_field] = element.text
        if isinstance(element.id, str):
            data[id_field] = element.id
        label_studio_data.append({"data": data})
    return label_studio_data
