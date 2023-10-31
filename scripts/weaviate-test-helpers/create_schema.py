import os

import weaviate

weaviate_host_url = os.getenv("WEAVIATE_HOST_URL", "http://localhost:8080")
class_name = os.getenv("WEAVIATE_CLASS_NAME", "pdf_elements")

class_schema = {
    "class": class_name,
    "vectorizer": "none",
}

client = weaviate.Client(
    url=weaviate_host_url,
)
if client.schema.exists(class_name):
    client.schema.delete_class(class_name)
client.schema.create_class(class_schema)
