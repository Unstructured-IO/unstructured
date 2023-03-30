import os
import pathlib

import pytest

from unstructured.partition.epub import partition_epub

DIRECTORY = pathlib.Path(__file__).parent.resolve()


@pytest.mark.xfail(reason="Requirements mismatch, should only fail in docker test")
def test_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


@pytest.mark.xfail(reason="Requirements mismatch, should only fail in docker test")
def test_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
