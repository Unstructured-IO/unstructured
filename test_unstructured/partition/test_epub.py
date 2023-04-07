import os
import pathlib

import pytest

from unstructured.partition.epub import partition_epub

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
