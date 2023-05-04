import os
import pathlib

import pypandoc
import pytest

from unstructured.documents.elements import Title
from unstructured.partition.odt import partition_odt

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

odt_not_supported = "odt" not in pypandoc.get_pandoc_formats()[0]
is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(odt_not_supported, reason="odt not supported in this version of pypandoc.")
def test_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename)
    assert elements == [Title("Lorem ipsum dolor sit amet.")]


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(odt_not_supported, reason="odt not supported in this version of pypandoc.")
def test_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f)

    assert elements == [Title("Lorem ipsum dolor sit amet.")]
