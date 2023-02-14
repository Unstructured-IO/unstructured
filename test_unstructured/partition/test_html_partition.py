import os
import pathlib
import pytest

from unstructured.partition.html import partition_html


DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_html_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    elements = partition_html(filename=filename)
    assert len(elements) > 0


def test_partition_html_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
        elements = partition_html(file=f)
    assert len(elements) > 0


def test_partition_html_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()
    elements = partition_html(text=text)
    assert len(elements) > 0


def test_partition_html_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_html()


def test_partition_html_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_html(filename=filename, text=text)
