from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, BinaryIO

import numpy as np
import pypdfium2 as pdfium

from unstructured.documents.elements import ElementType
from unstructured.partition.utils.constants import Source
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.layoutelement import LayoutElements


@requires_dependencies("unstructured_inference")
def process_data_with_pdfium(
    file: bytes | BinaryIO | None = None, fill=True, dpi=200
) -> list[LayoutElements]:
    from unstructured_inference.inference.layoutelement import LayoutElements

    pdf = pdfium.PdfDocument(file)
    all_layout = []

    for page_index in range(len(pdf)):
        page = pdf.get_page(page_index)
        textpage = page.get_textpage()

        # pdfium uses "\r\n" to mark pagebreaks; we drop \r
        text_with_linebreaks = textpage.get_text_bounded().replace("\r", "")
        texts, element_coords = [], []
        for i in range(textpage.count_rects()):
            bbox = textpage.get_rect(i)  # Returns (x0, y0, x1, y1)
            element_coords.append(bbox)
            texts.append(textpage.get_text_bounded(*bbox).replace("\r", "").lstrip())

        element_coords = np.array(element_coords)
        height = page.get_height()
        y2 = height - element_coords[:, 1]
        element_coords[:, 1] = height - element_coords[:, 3]
        element_coords[:, 3] = y2
        if fill:
            texts = repair_fragments(text_with_linebreaks, texts)

        layout = LayoutElements(
            element_coords=element_coords * dpi / 72,
            texts=np.array(texts).astype(object),
            element_class_ids=np.zeros((len(texts),)),
            element_class_id_map={0: ElementType.UNCATEGORIZED_TEXT, 1: ElementType.IMAGE},
            sources=np.array([Source.PDFMINER] * len(texts)),
        )
        all_layout.append(layout)

        page.close()

    pdf.close()
    return all_layout


def repair_fragments(text_line, fragments):
    pos = 0  # Position in text_line
    repaired = []
    len_text = len(text_line)
    len_frag = len(fragments)

    for ifrag, fragment in enumerate(fragments):
        # Look at remaining text_line
        remaining_text = text_line[pos:]

        # Use SequenceMatcher to align the fragment to the remaining text
        matcher = difflib.SequenceMatcher(None, remaining_text, fragment)
        match = matcher.find_longest_match(0, len(remaining_text), 0, len(fragment))

        if match.size == 0:
            repaired.append("")
            continue  # Skip fragment if no match found

        # Extract matched portion from the ground truth
        match_end = match.a + match.size
        matched_text = remaining_text[match.a : match_end]
        # Advance position in text_line
        new_pos = pos + match.a + match.size

        if (
            (new_pos < len_text and ifrag < len_frag)
            and remaining_text[match_end] == "\n"
            and not fragments[ifrag + 1].startswith("\n")
        ):
            matched_text += "\n"
            new_pos += 1
        repaired.append(matched_text)

        pos = new_pos

    return repaired


def refill_line_breaks(str_line: str, fragments: list[str]) -> list[str]:
    i_line = 0
    i_frag = 0
    len_frags = len(fragments)
    while i_line < len(str_line) and i_frag < len_frags - 1:
        end = str_line[i_line + len(fragments[i_frag])]
        if end == "\n":
            i_line += len(fragments[i_frag]) + 1
            fragments[i_frag] += end
        else:
            i_line += len(fragments[i_frag])
        i_frag += 1
    return fragments
