from __future__ import annotations

import os
import tempfile
from typing import IO

from unstructured.partition.common.common import exactly_one
from unstructured.utils import requires_dependencies


@requires_dependencies(["pypandoc"])
def convert_file_to_text(filename: str, source_format: str, target_format: str) -> str:
    """Uses pandoc to convert the source document to a raw text string."""
    import pypandoc

    try:
        text = pypandoc.convert_file(filename, target_format, format=source_format)
    except FileNotFoundError as err:
        msg = (
            f"Error converting the file to text. Ensure you have the pandoc package installed on"
            f" your system. Installation instructions are available at"
            f" https://pandoc.org/installing.html. The original exception text was:\n{err}"
        )
        raise FileNotFoundError(msg)
    except RuntimeError as err:
        supported_source_formats, _ = pypandoc.get_pandoc_formats()

        if source_format == "rtf" and source_format not in supported_source_formats:
            additional_info = (
                "Support for RTF files is not available in the current pandoc installation. "
                "It was introduced in pandoc 2.14.2.\n"
                "Reference: https://pandoc.org/releases.html#pandoc-2.14.2-2021-08-21"
            )
        else:
            additional_info = ""

        msg = (
            f"{err}\n\n{additional_info}\n\n"
            f"Current version of pandoc: {pypandoc.get_pandoc_version()}\n"
            "Make sure you have the right version installed in your system. Please follow the"
            " pandoc installation instructions in README.md to install the right version."
        )
        raise RuntimeError(msg)

    return text


def convert_file_to_html_text_using_pandoc(
    source_format: str, filename: str | None = None, file: IO[bytes] | None = None
) -> str:
    """Converts a document to HTML raw text.

    Enables the doucment to be processed using `partition_html()`.
    """
    exactly_one(filename=filename, file=file)

    if file is not None:
        with tempfile.TemporaryDirectory() as temp_dir_path:
            tmp_file_path = os.path.join(temp_dir_path, f"tmp_file.{source_format}")
            with open(tmp_file_path, "wb") as tmp_file:
                tmp_file.write(file.read())
            return convert_file_to_text(
                filename=tmp_file_path, source_format=source_format, target_format="html"
            )

    assert filename is not None
    return convert_file_to_text(
        filename=filename, source_format=source_format, target_format="html"
    )
