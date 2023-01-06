from typing import Dict, IO, List, Optional

from unstructured.file_utils.filetype import detect_filetype, FileType
from unstructured.partition.docx import partition_docx
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.pdf import partition_pdf


def partition(filename: Optional[str] = None, file: Optional[IO] = None):
    """Partitions a document into its constituent elements. Will use libmagic to determine
    the file's type and route it to the appropriate partitioning function. Applies the default
    parameters for each partitioning function. Use the document-type specific partitioning
    functions if you need access to additional kwarg options.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """
    pass
