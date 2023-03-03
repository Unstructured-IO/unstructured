import os
import pathlib

import pytest

from typing import IO, List, Optional
from unstructured.documents.elements import Address, ListItem, NarrativeText, Title
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json
from unstructured.partition.json import partition_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()

test_files = [
    "fake-text.txt",
    "layout-parser-paper-fast.pdf",
    "factbook.xml",
    "fake-html.html",
    "fake.doc",
    "factbook.xsl",
    "fake-email.eml",
    "fake-power-point.ppt",
    "fake.docx",
    "fake-power-point.pptx"
]


@pytest.mark.parametrize("filename", test_files)
def test_partition_text_from_filename(filename: str):
    root, _ = os.path.splitext(filename)
    
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    test_path = os.path.join(DIRECTORY, "test_json_output", root+".json")
    elements_to_json(elements, filename=test_path, indent=2)
    
    test_elements = partition_json(filename=test_path)
    
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


@pytest.mark.parametrize("filename", test_files)
def test_partition_text_from_file(filename: str):
    root, _ = os.path.splitext(filename)
    
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    test_path = os.path.join(DIRECTORY, "test_json_output", root+".json")
    elements_to_json(elements, filename=test_path, indent=2)
    
    with open(test_path) as f:
        test_elements = partition_json(file=f)
    
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]  


@pytest.mark.parametrize("filename", test_files)
def test_partition_text_from_text(filename: str):
    root, _ = os.path.splitext(filename)
    
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    test_path = os.path.join(DIRECTORY, "test_json_output", root+".json")
    elements_to_json(elements, filename=test_path, indent=2)
    
    with open(test_path) as f:
        text = f.read()
    test_elements = partition_json(text=text)

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_partition_text_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_json()


def test_partition_text_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "test_json_output", "fake-text.json")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_json(filename=filename, file=f)
    
    with pytest.raises(ValueError):
        partition_json(filename=filename, text=text)
    
    with pytest.raises(ValueError):
        partition_json(file=f, text=text)
    
    with pytest.raises(ValueError):
        partition_json(filename=filename, file=f, text=text)
