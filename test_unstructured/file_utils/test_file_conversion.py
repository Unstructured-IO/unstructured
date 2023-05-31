import os
import pathlib
from unittest.mock import patch

import pypandoc
import pytest

from unstructured.file_utils.file_conversion import convert_file_to_text

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_convert_file_to_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    html_text = convert_file_to_text(filename, source_format="epub", target_format="html")
    assert html_text.startswith("<p>")


def test_convert_to_file_raises_if_pandoc_not_available():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with patch.object(pypandoc, "convert_file", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            convert_file_to_text(filename, source_format="epub", target_format="html")
