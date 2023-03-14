from typing import IO, Optional

from unstructured.file_utils.filetype import FileType, detect_filetype
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import partition_docx
from unstructured.partition.email import partition_email
from unstructured.partition.epub import partition_epub
from unstructured.partition.html import partition_html
from unstructured.partition.image import partition_image
from unstructured.partition.json import partition_json
from unstructured.partition.md import partition_md
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.ppt import partition_ppt
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.text import partition_text


def partition(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    encoding: str = "utf-8",
):
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
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    strategy
        The strategy to use for partitioning the PDF. Uses a layout detection model if set
        to 'hi_res', otherwise partition_pdf simply extracts the text from the document
        and processes it.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    """
    filetype = detect_filetype(filename=filename, file=file)

    if file is not None:
        file.seek(0)

    if filetype == FileType.DOC:
        return partition_doc(filename=filename, file=file)
    if filetype == FileType.DOCX:
        return partition_docx(filename=filename, file=file)
    elif filetype == FileType.EML:
        return partition_email(filename=filename, file=file, encoding=encoding)
    elif filetype == FileType.HTML:
        return partition_html(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
        )
    elif filetype == FileType.EPUB:
        return partition_epub(filename=filename, file=file, include_page_breaks=include_page_breaks)
    elif filetype == FileType.MD:
        return partition_md(filename=filename, file=file, include_page_breaks=include_page_breaks)
    elif filetype == FileType.PDF:
        return partition_pdf(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
            strategy=strategy,
        )
    elif (filetype == FileType.PNG) or (filetype == FileType.JPG):
        return partition_image(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.TXT:
        return partition_text(filename=filename, file=file, encoding=encoding)
    elif filetype == FileType.PPT:
        return partition_ppt(filename=filename, file=file, include_page_breaks=include_page_breaks)
    elif filetype == FileType.PPTX:
        return partition_pptx(filename=filename, file=file, include_page_breaks=include_page_breaks)
    elif filetype == FileType.JSON:
        return partition_json(filename=filename, file=file)
    else:
        msg = "Invalid file" if not filename else f"Invalid file {filename}"
        raise ValueError(f"{msg}. The {filetype} file type is not supported in partition.")
