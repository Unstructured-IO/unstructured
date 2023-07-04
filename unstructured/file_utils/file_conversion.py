import tempfile
from typing import IO, Optional

import pypandoc

from unstructured.partition.common import exactly_one


def convert_file_to_text(filename: str, source_format: str, target_format: str) -> str:
    """Uses pandoc to convert the source document to a raw text string."""
    try:
        text = pypandoc.convert_file(filename, target_format, format=source_format)
    except FileNotFoundError as err:
        msg = (
            "Error converting the file to text. Ensure you have the pandoc "
            "package installed on your system. Install instructions are available at "
            "https://pandoc.org/installing.html. The original exception text was:\n"
            f"{err}"
        )
        raise FileNotFoundError(msg)

    return text


def convert_file_to_html_text(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
) -> str:
    """Converts a document to HTML raw text. Enables the doucment to be
    processed using the partition_html function."""
    exactly_one(filename=filename, file=file)

    if file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        html_text = convert_file_to_text(
            filename=tmp.name,
            source_format=source_format,
            target_format="html",
        )
    elif filename is not None:
        html_text = convert_file_to_text(
            filename=filename,
            source_format=source_format,
            target_format="html",
        )

    return html_text
