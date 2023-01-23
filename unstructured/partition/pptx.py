from typing import IO, List, Optional

import pptx

from unstructured.documents.elements import Element, ListItem, NarrativeText, Title
from unstructured.partition.text_type import (
    is_possible_narrative_text,
    is_possible_title,
)


OPENXML_SCHEMA_NAME = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def partition_pptx(filename: Optional[str] = None, file: Optional[IO] = None) -> List[Element]:
    """Partitions Microsoft PowerPoint Documents in .pptx format into its document elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """

    if not any([filename, file]):
        raise ValueError("One of filename or file must be specified.")

    if filename is not None and not file:
        presentation = pptx.Presentation(filename)
    elif file is not None and not filename:
        presentation = pptx.Presentation(file)
    else:
        raise ValueError("Only one of filename or file can be specified.")

    elements: List[Element] = list()
    for slide in presentation.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text
                if text.strip() == "":
                    continue
                if _is_bulleted_paragraph(paragraph):
                    elements.append(ListItem(text=text))
                elif is_possible_narrative_text(text):
                    elements.append(NarrativeText(text=text))
                elif is_possible_title(text):
                    elements.append(Title(text=text))

    return elements


def _is_bulleted_paragraph(paragraph) -> bool:
    """Determines if the paragraph is bulleted by looking for a bullet character prefix. Bullet
    characters in the openxml schema are represented by buChar"""
    paragraph_xml = paragraph._p.get_or_add_pPr()
    buChar = paragraph_xml.find(f"{OPENXML_SCHEMA_NAME}buChar")
    return buChar is not None
