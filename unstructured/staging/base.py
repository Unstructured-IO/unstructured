import io
import csv
from typing import Dict, List

from unstructured.documents.elements import Text


def convert_to_isd(elements: List[Text]) -> List[Dict[str, str]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, str]] = list()
    for element in elements:
        section = dict(text=element.text, type=element.category)
        isd.append(section)
    return isd


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
