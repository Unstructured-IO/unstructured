import os
import subprocess
import tempfile
from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.partition.docx import partition_docx


def partition_doc(filename: Optional[str] = None, file: Optional[IO] = None) -> List[Element]:
    """Partitions Microsoft Word Documents in .doc format into its document elements.

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
        _, filename_no_path = os.path.split(os.path.abspath(filename))
        base_filename, _ = os.path.splitext(filename_no_path)
    elif file is not None and not filename:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        _, filename_no_path = os.path.split(os.path.abspath(tmp.name))
    else:
        raise ValueError("Only one of filename or file can be specified.")

    base_filename, _ = os.path.splitext(filename_no_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _convert_to_docx(filename, tmpdir)
        docx_filename = os.path.join(tmpdir, f"{base_filename}.docx")
        elements = partition_docx(filename=docx_filename)

    return elements


def _convert_to_docx(input_filename, output_directory):
    """Converts a .doc file to a .docx file using the libreoffice CLI."""
    # NOTE(robinson) - In the future can also include win32com client as a fallback for windows
    # users who do not have LibreOffice installed
    # ref: https://stackoverflow.com/questions/38468442/
    #       multiple-doc-to-docx-file-conversion-using-python
    try:
        subprocess.call(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                output_directory,
                input_filename,
            ]
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            """soffice command was not found. Please install libreoffice
on your system and try again.

- Install instructions: https://www.libreoffice.org/get-help/install-howto/
- Mac: https://formulae.brew.sh/cask/libreoffice
- Debian: https://wiki.debian.org/LibreOffice"""
        )
