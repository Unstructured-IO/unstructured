#!/usr/bin/env python3

import os

import weaviate

from unstructured.staging.weaviate import create_unstructured_weaviate_class

weaviate_host_url = os.getenv("WEAVIATE_HOST_URL", "http://localhost:8080")
class_name = os.getenv("WEAVIATE_CLASS_NAME", "pdf_elements")

class_schema = {
    "class": class_name,
    "vectorizer": "none",
    "properties": [
        {"name": "element_id", "dataType": ["text"]},
        {"name": "text", "dataType": ["text"]},
        {"name": "type", "dataType": ["text"]},
        {
            "dataType": ["object"],
            "name": "metadata",
            "nestedProperties": [
                {"name": "category_depth", "dataType": ["int"]},
                {"name": "parent_id", "dataType": ["text"]},
                {"name": "attached_to_filename", "dataType": ["text"]},
                {"name": "filetype", "dataType": ["text"]},
                {"name": "last_modified", "dataType": ["date"]},
                {"name": "file_directory", "dataType": ["text"]},
                {"name": "filename", "dataType": ["text"]},
                {
                    "dataType": ["object"],
                    "name": "data_source",
                    "nestedProperties": [
                        {"name": "url", "dataType": ["text"]},
                        {"name": "version", "dataType": ["text"]},
                        {"name": "date_created", "dataType": ["date"]},
                        {"name": "date_modified", "dataType": ["date"]},
                        {"name": "date_processed", "dataType": ["date"]},
                        {"name": "record_locator", "dataType": ["text"]},
                    ],
                },
                {
                    "dataType": ["object"],
                    "name": "coordinates",
                    "nestedProperties": [
                        {"name": "system", "dataType": ["text"]},
                        {"name": "layout_width", "dataType": ["number"]},
                        {"name": "layout_height", "dataType": ["number"]},
                        {"name": "points", "dataType": ["text"]},
                    ],
                },
                {"name": "languages", "dataType": ["text[]"]},
                {"name": "page_number", "dataType": ["int"]},
                {"name": "page_name", "dataType": ["text"]},
                {"name": "url", "dataType": ["text"]},
                {"name": "link_urls", "dataType": ["text[]"]},
                {"name": "link_texts", "dataType": ["text[]"]},
                {"name": "sent_from", "dataType": ["text"]},
                {"name": "sent_to", "dataType": ["text"]},
                {"name": "subject", "dataType": ["text"]},
                {"name": "section", "dataType": ["text"]},
                {"name": "header_footer_type", "dataType": ["text"]},
                {"name": "emphasized_text_contents", "dataType": ["text[]"]},
                {"name": "emphasized_text_tags", "dataType": ["text[]"]},
                {"name": "text_as_html", "dataType": ["text"]},
                {"name": "regex_metadata", "dataType": ["text"]},
                {"name": "detection_class_prob", "dataType": ["number"]},
            ],
        },
    ],
}

client = weaviate.Client(
    url=weaviate_host_url,
)
new_class = create_unstructured_weaviate_class(class_name)
if client.schema.exists(class_name):
    client.schema.delete_class(class_name)
client.schema.create_class(new_class)
