import jsonschema

_coordinates_schema = {
    "type": "object",
    "properties": {
        "system": {"type": "string"},
        "layout_width": {"type": "number"},
        "layout_height": {"type": "number"},
        "points": {
            "type": "array",
            "items": {
                "type": "array",
                "maxItems": 2,
                "minItems": 2,
                "items": {
                    "type": "number",
                },
            },
        },
    },
}

_data_source_schema = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "version": {"type": "string"},
        "record_locator": {"type": "object"},
        "date_created": {"type": "string"},
        "date_modified": {"type": "string"},
        "date_processed": {"type": "string"},
    },
}

_metadata_schema = {
    "type": "object",
    "properties": {
        "coordinates": _coordinates_schema,
        "data_source": _data_source_schema,
        "filename": {"type": "string"},
        "file_directory": {"type": "string"},
        "last_modified": {"type": "string"},
        "filetype": {"type": "string"},
        "attached_to_filename": {"type": "string"},
        "parent_id": {"type": "string"},
        "category_depth": {"type": "integer"},
        "page_numbed": {"type": "integer"},
        "page_name": {"type": "string"},
        "url": {"type": "string"},
        "link_urls": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "link_texts": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "sent_from": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "sent_to": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "subject": {"type": "string"},
        "section": {"type": "string"},
        "header_footer_type": {"type": "string"},
        "emphasized_text_contents": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "emphasized_text_tags": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "text_as_html": {"type": "string"},
        "regex_metadata": {"type": "object"},
        "detection_class_prob": {"type": "number"},
    },
}

_element_schema = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
        },
        "element_id": {
            "type": "string",
        },
        "type": {
            "type": ["string", "null"],
        },
        "metadata": _metadata_schema,
    },
    "required": ["metadata", "element_id"],
}

_schema = {
    "type": "array",
    "items": _element_schema,
}


def get_schema() -> dict:
    try:
        jsonschema.validate({}, schema=_schema)
    except jsonschema.SchemaError as error:
        raise ValueError(f"json schema is invalid: {error}") from error

    return _schema
