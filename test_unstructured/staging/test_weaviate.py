import json
import os

import pytest
from weaviate.schema.validate_schema import validate_schema

from unstructured.partition.json import partition_json
from unstructured.staging.weaviate import (
    create_unstructured_weaviate_class,
    stage_for_weaviate,
)

is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_stage_for_weaviate(filename="example-docs/layout-parser-paper-fast.pdf"):
    element_dict = {
        "element_id": "015301d4f56aa4b20ec10ac889d2343f",
        "coordinates": (
            (157.62199999999999, 114.23496279999995),
            (157.62199999999999, 146.5141628),
            (457.7358962799999, 146.5141628),
            (457.7358962799999, 114.23496279999995),
        ),
        "text": "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis",
        "type": "Title",
        "metadata": {
            "filename": "layout-parser-paper-fast.pdf",
            "filetype": "application/json",
            "page_number": 1,
        },
    }

    elements = partition_json(text=json.dumps([element_dict]))
    data = stage_for_weaviate(elements)
    assert data[0] == {
        "filename": "layout-parser-paper-fast.pdf",
        "filetype": "application/json",
        "page_number": 1,
        "text": "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis",
        "category": "Title",
    }


def test_weaviate_schema_is_valid():
    unstructured_class = create_unstructured_weaviate_class()
    schema = {"classes": [unstructured_class]}
    validate_schema(schema)
