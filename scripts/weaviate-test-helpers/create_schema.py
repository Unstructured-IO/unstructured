#!/usr/bin/env python3

import json
import os

import weaviate

weaviate_host_url = os.getenv("WEAVIATE_HOST_URL", "http://localhost:8080")
class_name = os.getenv("WEAVIATE_CLASS_NAME", "Elements")
new_class = None

with open("./scripts/weaviate-test-helpers/elements.json") as f:
    new_class = json.load(f)

client = weaviate.Client(
    url=weaviate_host_url,
)

if client.schema.exists(class_name):
    client.schema.delete_class(class_name)
client.schema.create_class(new_class)
