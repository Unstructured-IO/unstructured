import tempfile
from typing import IO, Optional

from unstructured.partition.common import exactly_one
from unstructured.utils import dependency_exists, requires_dependencies

if dependency_exists("pypandoc"):
    import pypandoc


@requires_dependencies(["pypandoc"])
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
            "Make sure you have the right version installed in your system. "
            "Please, follow the pandoc installation instructions "
            "in README.md to install the right version."
        )
        raise RuntimeError(msg)

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
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(file.read())
            tmp.flush()

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
