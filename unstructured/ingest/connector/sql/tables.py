import typing as t

from unstructured.utils import requires_dependencies

ELEMENTS_TABLE_NAME = "elements"
METADATA_TABLE_NAME = "metadata"
DATA_SOURCE_TABLE_NAME = "data_source"
COORDINATES_TABLE_NAME = "coordinates"


def make_elements_table(table_name: str, dialect: str, metadata):
    from sqlalchemy import ARRAY, DECIMAL, Column, String, Table

    array_type = ARRAY(DECIMAL) if dialect == "postgresql" else String

    return Table(
        table_name,
        metadata,
        Column("id", String),
        Column("element_id", String),
        Column("text", String),
        Column("embeddings", array_type),
        Column("type", String),
        Column("metadata_id", String(36)),
    )


def make_metadata_table(table_name: str, dialect: str, metadata):
    from sqlalchemy import ARRAY, DECIMAL, TIMESTAMP, Column, Integer, String, Table

    array_type = ARRAY(DECIMAL) if dialect == "postgresql" else String

    return Table(
        table_name,
        metadata,
        Column("id", String(36)),
        Column("category_depth", Integer),
        Column("parent_id", String),
        Column("attached_filename", String),
        Column("filetype", String),
        Column("last_modified", TIMESTAMP(timezone=True)),
        Column("file_directory", String),
        Column("filename", String),
        Column("page_number", String),
        Column("links", String),
        Column("url", String),
        Column("link_texts", array_type),
        Column("sent_from", array_type),
        Column("sent_to", array_type),
        Column("subject", String),
        Column("section", String),
        Column("header_footer_type", String),
        Column("emphasized_text_contents", array_type),
        Column("text_as_html", String),
        Column("regex_metadata", String),
        Column("detection_class_prob", DECIMAL()),
        Column("data_source_id", String(36)),
        Column("coordinates_id", String(36)),
    )


def make_data_source_table(table_name: str, metadata):
    from sqlalchemy import TIMESTAMP, Column, String, Table

    return Table(
        table_name,
        metadata,
        Column("id", String(36)),
        Column("url", String),
        Column("version", String),
        Column("date_created", TIMESTAMP(timezone=True)),
        Column("date_modified", TIMESTAMP(timezone=True)),
        Column("date_processed", TIMESTAMP(timezone=True)),
        Column("permissions_data", String),
        Column("record_locator", String),
    )


def make_coordinates_table(table_name: str, metadata):
    from sqlalchemy import DECIMAL, Column, String, Table

    return Table(
        table_name,
        metadata,
        Column("id", String(36)),
        Column("system", String),
        Column("layout_width", DECIMAL()),
        Column("layout_height", DECIMAL()),
        Column("points", String),
    )


@requires_dependencies(["sqlalchemy"], extras="sql")
def make_schema(table_name_mapping: t.Dict, dialect: str, meta=None) -> dict:
    """
    Returns a Dict[str, sqlalchemy.Table] object with the required tables
    to store partitioned data on any of the relational databases supported
    by SQLAlchemy.
    """

    from sqlalchemy import MetaData

    metadata = meta or MetaData()

    elements = make_elements_table(table_name_mapping[ELEMENTS_TABLE_NAME], dialect, metadata)

    meta_table = make_metadata_table(table_name_mapping[METADATA_TABLE_NAME], dialect, metadata)

    data_source = make_data_source_table(table_name_mapping[DATA_SOURCE_TABLE_NAME], metadata)

    coordinates = make_coordinates_table(table_name_mapping[COORDINATES_TABLE_NAME], metadata)

    return {
        ELEMENTS_TABLE_NAME: elements,
        METADATA_TABLE_NAME: meta_table,
        DATA_SOURCE_TABLE_NAME: data_source,
        COORDINATES_TABLE_NAME: coordinates,
    }


@requires_dependencies(["sqlalchemy"], extras="sql")
def check_schema_exists(engine, table_name_mapping: t.Dict[str, str]) -> bool:
    """Checks if the schema tables exist in the database"""
    from sqlalchemy import inspect

    insp = inspect(engine)
    return all(insp.has_table(table) for table in table_name_mapping.values())


@requires_dependencies(["sqlalchemy"], extras="sql")
def create_schema(engine, table_name_mapping: t.Dict[str, str]) -> dict:
    """Creates the tables in the database"""
    from sqlalchemy import MetaData

    meta = MetaData()
    schema = make_schema(table_name_mapping, engine.dialect.__str__, meta)
    meta.create_all(engine)
    return schema


@requires_dependencies(["sqlalchemy"], extras="sql")
def drop_schema(engine, table_name_mapping: t.Dict[str, str]):
    """Removes the tables in the database"""
    from sqlalchemy import MetaData

    meta = MetaData()
    schema = make_schema(table_name_mapping, engine.dialect.__str__, meta)
    meta.drop_all(engine, tables=schema.values())
