import io
import csv
from typing import Dict, List

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
