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
    def __init__(self, conn, db_name, table_name_mapping, table_column_mapping) -> None:
        self.db_name = db_name
        self.cursor = conn.cursor()
        self.placeholder = "?" if db_name == "sqlite" else "%s"
        self.table_name_mapping = table_name_mapping
        self.table_column_mapping = table_column_mapping

    def insert(
        self,
        table,
        table_name: str,
        data: t.Dict[str, any],
    ) -> None:
        columns = []
        values = []

        for c in TABLE_COLUMN_NAMES[table]:
            if c in data:
                column_name = (
                    c
                    if (self.table_column_mapping is None)
                    else self.table_column_mapping.get(c, c)
                )
                columns.append(column_name)
                values.append(data[c])

        query = (
            f"INSERT INTO {table_name} ({','.join(columns)}) "
            f"VALUES ({','.join([self.placeholder for _ in values])})"
        )

        self.cursor.execute(query, values)

    def clear_schema(self):
        tables = [
            self.table_name_mapping[v]
            for v in [
                COORDINATES_TABLE_NAME,
                DATA_SOURCE_TABLE_NAME,
                METADATA_TABLE_NAME,
                ELEMENTS_TABLE_NAME,
            ]
        ]
        query = "; ".join([f"DELETE FROM {x}" for x in tables])
        self.cursor.execute(query)

    def check_schema_exists(self):
        elements_table_name = (
            ELEMENTS_TABLE_NAME
            if (self.table_name_mapping is None)
            else self.table_name_mapping.get(ELEMENTS_TABLE_NAME, ELEMENTS_TABLE_NAME)
        )
        query = f"SELECT id FROM {elements_table_name} LIMIT 1;"
        result = self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            return False
        return True
