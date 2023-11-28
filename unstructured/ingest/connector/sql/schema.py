import typing as t

ELEMENTS_TABLE_NAME = "elements"
METADATA_TABLE_NAME = "metadata"
DATA_SOURCE_TABLE_NAME = "data_source"
COORDINATES_TABLE_NAME = "coordinates"

TABLE_COLUMN_NAMES = {
    ELEMENTS_TABLE_NAME: {"id", "element_id", "text", "embeddings", "type", "metadata_id"},
    METADATA_TABLE_NAME: {
        "id",
        "category_depth",
        "parent_id",
        "attached_filename",
        "filetype",
        "last_modified",
        "file_directory",
        "filename",
        "page_number",
        "links",
        "url",
        "link_texts",
        "sent_from",
        "sent_to",
        "subject",
        "section",
        "header_footer_type",
        "emphasized_text_contents",
        "text_as_html",
        "regex_metadata",
        "detection_class_prob",
        "data_source_id",
        "coordinates_id",
    },
    DATA_SOURCE_TABLE_NAME: {
        "id",
        "url",
        "version",
        "date_created",
        "date_modified",
        "date_processed",
        "permissions_data",
        "record_locator",
    },
    COORDINATES_TABLE_NAME: {"id", "system", "layout_width", "layout_height", "type", "points"},
}


class DatabaseSchema:
    def __init__(self, conn, db_name) -> None:
        self.db_name = db_name
        self.cursor = conn.cursor()
        self.placeholder = "?" if db_name == "sqlite" else "%s"

    def insert(
        self,
        table_name: t.List,
        data: t.Dict[str, any],
        table_column_mapping: t.Dict[str, str] = None,
    ) -> None:
        columns = []
        values = []

        for c in TABLE_COLUMN_NAMES[table_name]:
            if c in data:
                column_name = (
                    c if (table_column_mapping is None) else table_column_mapping.get(c, c)
                )
                columns.append(column_name)
                values.append(data[c])

        query = (
            f"INSERT INTO {table_name} ({','.join(columns)}) "
            f"VALUES ({','.join([self.placeholder for _ in values])})"
        )

        self.cursor.execute(query, values)

    def drop_schema(self, table_name_mapping):
        tables = [
            table_name_mapping[v]
            for v in [
                COORDINATES_TABLE_NAME,
                DATA_SOURCE_TABLE_NAME,
                METADATA_TABLE_NAME,
                ELEMENTS_TABLE_NAME,
            ]
        ]
        query = f"DROP TABLE {','.join(tables)}"

        self.cursor.execute(query)

    def check_schema_exists(self, table_name_mapping: t.Optional[t.Dict[str, str]] = None):
        elements_table_name = (
            ELEMENTS_TABLE_NAME
            if (table_name_mapping is None)
            else table_name_mapping.get(ELEMENTS_TABLE_NAME, ELEMENTS_TABLE_NAME)
        )
        query = f"SELECT id FROM {elements_table_name} LIMIT 1;"
        result = self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            return False
        return True
