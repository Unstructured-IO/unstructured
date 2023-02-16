import io
import csv
from typing import Any, Dict, List

import pandas as pd

from unstructured.documents.elements import Text, NarrativeText, Title, ListItem

TABLE_FIELDNAMES: List[str] = ["type", "text", "filename", "page_number", "url"]


def convert_to_isd(elements: List[Text]) -> List[Dict[str, str]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, str]] = list()
    for element in elements:
        section = element.to_dict()
        isd.append(section)
    return isd


def isd_to_elements(isd: List[Dict[str, str]]) -> List[Text]:
    """Converts an Initial Structured Data (ISD) dictionary to a list of Text elements."""
    elements: List[Text] = list()

    for item in isd:
        if item["type"] == "NarrativeText":
            elements.append(NarrativeText(text=item["text"]))
        elif item["type"] == "Title":
            elements.append(Title(text=item["text"]))
        # NOTE(robinson) - "BulletedText" is in there for backward compatibility. ListItem used
        # to be called BulletedText in an earlier version
        elif item["type"] in ["ListItem", "BulletedText"]:
            elements.append(ListItem(text=item["text"]))

    return elements


def convert_to_isd_csv(elements: List[Text]) -> str:
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


def convert_to_dataframe(elements: List[Text]) -> pd.DataFrame:
    """Converts document elements to a pandas DataFrame. The dataframe contains the
    following columns:
        text: the element text
        type: the text type (NarrativeText, Title, etc)
    """
    csv_string = convert_to_isd_csv(elements)
    csv_string_io = io.StringIO(csv_string)
    return pd.read_csv(csv_string_io, sep=",")
