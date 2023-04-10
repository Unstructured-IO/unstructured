import os
import pathlib

import pytest

from unstructured.documents.elements import Title
from unstructured.partition.rtf import partition_rtf

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_partition_rtf_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_partition_rtf_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
