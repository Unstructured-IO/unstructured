import os
import pathlib
import pytest
import re

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
    with open(filename, "r") as f:
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


def test_partition_html_includes_javascript_function():
    regex_for_js_function = (
        r"function\s*([A-z0-9]+)?\s*\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)"
        r"\s*\{(?:[^}{]+|\{(?:[^}{]+|\{[^}{]*\})*\})*\}"
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-script-html.html")
    with open(filename, "r") as f:
        file_text = f.read()
    elements = partition_html(text=file_text)
    text = "\n\n".join([str(el) for el in elements[:5]])
    content = re.search(regex_for_js_function, text, flags=0)
    check_js = True if content else False
    assert check_js is False
