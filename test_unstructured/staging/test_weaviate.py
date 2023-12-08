import contextlib
import json
import os

import pytest

# NOTE(robinson) - allows tests that do not require the weaviate client to
# run for the docker container
with contextlib.suppress(ModuleNotFoundError):
    from weaviate import Client
    from weaviate.embedded import EmbeddedOptions

from unstructured.partition.json import partition_json
from unstructured.staging.weaviate import (
    create_unstructured_weaviate_class,
    stage_for_weaviate,
)

is_in_docker = os.path.exists("/.dockerenv")


def test_stage_for_weaviate(filename="example-docs/layout-parser-paper-fast.pdf"):
    element_dict = {
        "element_id": "015301d4f56aa4b20ec10ac889d2343f",
        "text": "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis",
        "type": "Title",
        "metadata": {
            "filename": "layout-parser-paper-fast.pdf",
            "filetype": "application/json",
            "page_number": 1,
            "coordinates": {
                "points": (
                    (157.62199999999999, 114.23496279999995),
                    (157.62199999999999, 146.5141628),
                    (457.7358962799999, 146.5141628),
                    (457.7358962799999, 114.23496279999995),
                ),
                "system": "PixelSpace",
                "layout_width": 324,
                "layout_height": 450,
            },
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


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_weaviate_schema_is_valid():
    unstructured_class = create_unstructured_weaviate_class()
    schema = {"classes": [unstructured_class]}
    client = Client(embedded_options=EmbeddedOptions())
    client.schema.create(schema)
