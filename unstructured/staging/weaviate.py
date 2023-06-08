from typing import Any, Dict, List, TypedDict

from unstructured.documents.elements import ElementMetadata, Text


class Properties(TypedDict):
    name: str
    dataType: List[str]


def stage_for_weaviate(elements: List[Text]) -> List[Dict[str, Any]]:
    """Converts a list of elements into a list of dictionaries that can be uploaded to
    Weaviate. The outputs will conform to the schema created with
    create_unstructured_weaviate_class.

    References
    ----------
    https://weaviate.io/developers/weaviate/tutorials/import#batch-import-process
    """
    data: List[Dict[str, Any]] = []
    for element in elements:
        properties = element.metadata.to_dict()
        properties["text"] = element.text
        properties["category"] = element.category
        data.append(properties)

    return data


def create_unstructured_weaviate_class(class_name: str = "UnstructuredDocument"):
    """Creates a Weaviate schema class for Unstructured documents using the information
    available in ElementMetadata.


    Parameters
    ----------
    class_name: str
        The name to use for the Unstructured class in the schema.
        Defaults to "UnstructuredDocument".

    References
    ----------
    https://weaviate.io/developers/weaviate/client-libraries/python#manual-batching
    """
    properties: List[Properties] = [
        {
            "name": "text",
            "dataType": ["text"],
        },
        {
            "name": "category",
            "dataType": ["text"],
        },
    ]

    exclude_metadata_keys = ["data_source"]

    for name, annotation in ElementMetadata.__annotations__.items():
        if name not in exclude_metadata_keys:
            data_type = _annotation_to_weaviate_data_type(annotation)
            properties.append(
                {
                    "name": name,
                    "dataType": data_type,
                },
            )

    class_dict = {
        "class": class_name,
        "properties": properties,
    }

    return class_dict


def _annotation_to_weaviate_data_type(annotation: str):
    if "str" in annotation:
        return ["text"]
    elif "int" in annotation:
        return ["int"]
    elif "date" in annotation:
        return ["date"]
    else:
        raise ValueError(f"Annotation {annotation} does not map to a Weaviate dataType.")
