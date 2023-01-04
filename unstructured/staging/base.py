import io
import csv
from typing import Dict, List

import pandas as pd

from unstructured.documents.elements import Text, NarrativeText, Title, ListItem


def convert_to_isd(elements: List[Text]) -> List[Dict[str, str]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, str]] = list()
    for element in elements:
        section = dict(text=element.text, type=element.category)
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
    csv_fieldnames: List[str] = ["type", "text"]
    rows: List[Dict[str, str]] = convert_to_isd(elements)
    with io.StringIO() as buffer:
        csv_writer = csv.DictWriter(buffer, fieldnames=csv_fieldnames)
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
