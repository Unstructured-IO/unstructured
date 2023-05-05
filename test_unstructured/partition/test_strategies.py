import os

import pytest

from unstructured.file_utils.filetype import FileType
from unstructured.partition import strategies


def test_validate_strategy_validates():
    # Nothing should raise for a valid strategy
    strategies.validate_strategy("hi_res", FileType.PDF)


def test_validate_strategy_raises_for_bad_filetype():
    with pytest.raises(ValueError):
        strategies.validate_strategy("fast", FileType.JPG)


def test_validate_strategy_raises_for_bad_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy("totally_guess_the_text", FileType.JPG)


@pytest.mark.parametrize(
    ("filename", "from_file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", True, True),
        ("copy-protected.pdf", True, False),
        ("layout-parser-paper-fast.pdf", False, True),
        ("copy-protected.pdf", False, False),
    ],
)
def test_is_pdf_text_extractable(filename, from_file, expected):
    filename = os.path.join("example-docs", filename)

    if from_file:
        with open(filename, "rb") as f:
            extractable = strategies.is_pdf_text_extractable(file=f)
    else:
        extractable = strategies.is_pdf_text_extractable(filename=filename)

    assert extractable is expected
