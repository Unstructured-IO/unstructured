import csv
import io
import json
from typing import Any, Dict, List, Optional

import pandas as pd

from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    Element,
    ElementMetadata,
    NoID,
)

TABLE_FIELDNAMES: List[str] = [
    "type",
    "text",
    "element_id",
    "coordinates",
    "filename",
    "page_number",
    "url",
]


def convert_to_isd(elements: List[Element]) -> List[Dict[str, str]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, str]] = []
    for element in elements:
        section = element.to_dict()
        isd.append(section)
    return isd


def convert_to_dict(elements: List[Element]) -> List[Dict[str, str]]:
    """Converts a list of elements into a dictionary."""
    return convert_to_isd(elements)


def elements_to_json(elements: List[Element], filename: str, indent: int = 4):
    """Saves a list of elements to a JSON file."""
    element_dict = convert_to_dict(elements)
    with open(filename, "w") as f:
        json.dump(element_dict, f, indent=indent)


def isd_to_elements(isd: List[Dict[str, Any]]) -> List[Element]:
    """Converts an Initial Structured Data (ISD) dictionary to a list of elements."""
    elements: List[Element] = []

    for item in isd:
        element_id: str = item.get("element_id", NoID())
        coordinates: Optional[List[float]] = item.get("coordinates")

        metadata = ElementMetadata()
        _metadata_dict = item.get("metadata")
        if _metadata_dict is not None:
            metadata = ElementMetadata.from_dict(_metadata_dict)

        if item["type"] in TYPE_TO_TEXT_ELEMENT_MAP:
            _text_class = TYPE_TO_TEXT_ELEMENT_MAP[item["type"]]
            elements.append(
                _text_class(
                    text=item["text"],
                    element_id=element_id,
                    metadata=metadata,
                    coordinates=coordinates,
                ),
            )
        elif item["type"] == "CheckBox":
            elements.append(
                CheckBox(
                    checked=item["checked"],
                    element_id=element_id,
                    metadata=metadata,
                    coordinates=coordinates,
                ),
            )

    return elements


def dict_to_elements(element_dict: List[Dict[str, Any]]) -> List[Element]:
    """Converts a dictionary representation of an element list into List[Element]."""
    return isd_to_elements(element_dict)


def elements_from_json(filename: str) -> List[Element]:
    """Loads a list of elements from a JSON file."""
    with open(filename) as f:
        element_dict = json.load(f)
    return dict_to_elements(element_dict)


def convert_to_isd_csv(elements: List[Element]) -> str:
    """
    Returns the representation of document elements as an Initial Structured Document (ISD)
    in CSV Format.
    """
    rows: List[Dict[str, Any]] = convert_to_isd(elements)
    # NOTE(robinson) - flatten metadata and add it to the table
    for row in rows:
        metadata = row.pop("metadata")
        for key, value in metadata.items():
            if key in TABLE_FIELDNAMES:
                row[key] = value

    with io.StringIO() as buffer:
        csv_writer = csv.DictWriter(buffer, fieldnames=TABLE_FIELDNAMES)
        csv_writer.writeheader()
        csv_writer.writerows(rows)
        return buffer.getvalue()


def convert_to_csv(elements: List[Element]) -> str:
    """Converts a list of elements to a CSV."""
    return convert_to_isd_csv(elements)


def convert_to_dataframe(elements: List[Element]) -> pd.DataFrame:
    """Converts document elements to a pandas DataFrame. The dataframe contains the
    following columns:
        text: the element text
        type: the text type (NarrativeText, Title, etc)
    """
    csv_string = convert_to_isd_csv(elements)
    csv_string_io = io.StringIO(csv_string)
    return pd.read_csv(csv_string_io, sep=",")
