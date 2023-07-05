from typing import Dict, List, TypedDict

from unstructured.documents.elements import Text
from unstructured.staging.base import flatten_dict


class BaseplateRow(TypedDict):
    """Typed dictionary for an individual Baseplate row. Baseplate docs show what the JSON
    representation should look like:
        https://docs.baseplate.ai/api-reference/documents/overview
    """

    data: Dict[str, str]
    metadata: Dict[str, str]


class BaseplateRows(TypedDict):
    """Typed dictionary for multiple Baseplate rows. Baseplate docs show what the JSON
    representation should look like. This is the JSON that is submitted to the Baseplate
    API to upload data.
        https://docs.baseplate.ai/api-reference/documents/overview
    """

    rows: List[BaseplateRow]


def stage_for_baseplate(elements: List[Text]) -> BaseplateRows:
    """Converts a list of unstructured elements into a dictionary of rows that can be uploaded
    into Baseplate via the API.

    References
    ----------
    https://docs.baseplate.ai/api-reference/documents/overview
    https://docs.baseplate.ai/api-reference/documents/upsert-data-rows
    """

    rows: List[BaseplateRow] = []
    for element in elements:
        element_dict = element.to_dict()
        metadata = element_dict.pop("metadata")
        row: BaseplateRow = {
            # Baseplate maps each key in the row's data object to a column in the dataset and
            # each key in the row's metadata object to a metadata column in the dataset.
            # We infer that Baseplate cannot map a nested object to a column in its dataset.
            "data": flatten_dict(element_dict),
            "metadata": flatten_dict(metadata),
        }
        rows.append(row)

    return {"rows": rows}
