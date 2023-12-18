import json
import typing as t

ELEMENTS_TABLE_NAME = "elements"

TABLE_COLUMN_NAMES = {
    ELEMENTS_TABLE_NAME: {
        "id",
        "element_id",
        "text",
        "embeddings",
        "type",
        "system",
        "layout_width",
        "layout_height",
        "points",
        "url",
        "version",
        "date_created",
        "date_modified",
        "date_processed",
        "permissions_data",
        "record_locator",
        "category_depth",
        "parent_id",
        "attached_filename",
        "filetype",
        "last_modified",
        "file_directory",
        "filename",
        "languages",
        "page_number",
        "links",
        "page_name",
        "link_urls",
        "link_texts",
        "sent_from",
        "sent_to",
        "subject",
        "section",
        "header_footer_type",
        "emphasized_text_contents",
        "emphasized_text_tags",
        "text_as_html",
        "regex_metadata",
        "detection_class_prob",
    },
}


class DatabaseSchema:
    def __init__(self, conn, db_name) -> None:
        self.db_name = db_name
        self.cursor = conn.cursor()
        self.placeholder = "?" if db_name == "sqlite" else "%s"

    def insert(
        self,
        table,
        data: t.Dict[str, any],
    ) -> None:
        columns = []
        values = []

        for col in TABLE_COLUMN_NAMES[table]:
            if col in data:
                columns.append(col)
                if self.db_name == "sqlite" and isinstance(data[col], list):
                    values.append(json.dumps(data[col]))
                else:
                    values.append(data[col])

        query = (
            f"INSERT INTO {table} ({','.join(columns)}) "
            f"VALUES ({','.join([self.placeholder for _ in values])})"
        )

        self.cursor.execute(query, values)

    def clear_schema(self):
        query = f"DELETE FROM {ELEMENTS_TABLE_NAME}"
        self.cursor.execute(query)

    def check_schema_exists(self):
        query = f"SELECT id FROM {ELEMENTS_TABLE_NAME} LIMIT 1;"
        result = self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            return False
        return True
