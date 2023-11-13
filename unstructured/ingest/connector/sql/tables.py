from unstructured.utils import requires_dependencies


@requires_dependencies(["sqlalchemy"], extras="sql")
def make_elements_table(table_name: str):
    from sqlalchemy import ARRAY, DECIMAL, Column, MetaData, String, Table

    meta = MetaData()
    return Table(
        table_name,
        meta,
        Column("id", String),
        Column("element_id", String),
        Column("text", String),
        Column("embeddings", ARRAY(DECIMAL())),
        Column("type", String),
        Column("metadata_id", String(36)),
    )


@requires_dependencies(["sqlalchemy"], extras="sql")
def make_metadata_table(table_name: str):
    from sqlalchemy import ARRAY, DECIMAL, TIMESTAMP, Column, Integer, MetaData, String, Table

    meta = MetaData()
    return Table(
        table_name,
        meta,
        Column("id", String(36)),
        Column("category_depth", Integer),
        Column("parent_id", String),
        Column("attached_filename", String),
        Column("filetype", String),
        Column("last_modified", TIMESTAMP(timezone=True)),
        Column("file_directory", String),
        Column("filename", String),
        Column("page_number", String),
        Column("links", ARRAY(String)),
        Column("url", String),
        Column("link_texts", ARRAY(String)),
        Column("sent_from", ARRAY(String)),
        Column("sent_to", ARRAY(String)),
        Column("subject", String),
        Column("section", String),
        Column("header_footer_type", String),
        Column("emphasized_text_contents", ARRAY(String)),
        Column("text_as_html", String),
        Column("regex_metadata", String),
        Column("detection_class_prob", DECIMAL()),
        Column("data_source_id", String(36)),
        Column("coordinates_id", String(36)),
    )


@requires_dependencies(["sqlalchemy"], extras="sql")
def make_data_source_table(table_name: str):
    from sqlalchemy import TIMESTAMP, Column, MetaData, String, Table

    meta = MetaData()
    return Table(
        table_name,
        meta,
        Column("id", String(36)),
        Column("url", String),
        Column("version", String),
        Column("date_created", TIMESTAMP(timezone=True)),
        Column("date_modified", TIMESTAMP(timezone=True)),
        Column("date_processed", TIMESTAMP(timezone=True)),
        Column("permissions_data", String),
        Column("record_locator", String),
    )


@requires_dependencies(["sqlalchemy"], extras="sql")
def make_coordinates_table(table_name: str):
    from sqlalchemy import DECIMAL, Column, MetaData, String, Table

    meta = MetaData()
    return Table(
        table_name,
        meta,
        Column("id", String(36)),
        Column("system", String),
        Column("layout_width", DECIMAL()),
        Column("layout_height", DECIMAL()),
        Column("points", String),
    )
