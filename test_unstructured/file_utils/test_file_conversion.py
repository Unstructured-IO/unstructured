import os
import pathlib
import tempfile
from unittest.mock import patch

import pypandoc
import pytest

from test_unstructured.unit_utils import FixtureRequest, example_doc_path, stdlib_fn_mock
from unstructured.file_utils.file_conversion import (
    convert_file_to_html_text_using_pandoc,
    convert_file_to_text,
)

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


@pytest.mark.parametrize(
    ("source_format", "filename"),
    [
        ("epub", "winter-sports.epub"),
        ("org", "README.org"),
        ("rst", "README.rst"),
        ("rtf", "fake-doc.rtf"),
    ],
)
def test_convert_file_to_html_text_using_pandoc(
    request: FixtureRequest, tmp_path: pathlib.Path, source_format: str, filename: str
):
    # -- Get a real tempdir: `tmp_path`
    # -- Mock tempfile.TemporaryDirectory() using `stdlib_fn_mock`
    # -- Set the return value of mock.__enter__ to the real tempdir
    tempdir_ = stdlib_fn_mock(request, tempfile, "TemporaryDirectory")
    tempdir_.return_value.__enter__.return_value = tmp_path

    with open(example_doc_path(filename), "rb") as f:
        html_text = convert_file_to_html_text_using_pandoc(file=f, source_format=source_format)

    assert isinstance(html_text, str)
    assert len(list(tmp_path.iterdir())) == 1
    tempdir_.return_value.__exit__.assert_called_once()
