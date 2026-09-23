import io
from typing import BinaryIO

import pypdf


def get_page_data(fp: BinaryIO, page_number: int):
    """Find the binary data for a given page number from a PDF binary file."""
    pdf_reader = pypdf.PdfReader(fp)
    pdf_writer = pypdf.PdfWriter()
    page = pdf_reader.pages[page_number]
    pdf_writer.add_page(page)
    page_data = io.BytesIO()
    pdf_writer.write(page_data)
    return page_data
