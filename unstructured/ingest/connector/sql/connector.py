import json
import typing as t
import uuid
from dataclasses import dataclass, field

from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

from .schema import (
    COORDINATES_TABLE_NAME,
    DATA_SOURCE_TABLE_NAME,
    ELEMENTS_TABLE_NAME,
    METADATA_TABLE_NAME,
    DatabaseSchema,
)


@dataclass
class SimpleSqlConfig(BaseConnectorConfig):
    db_name: t.Optional[str]
    username: t.Optional[str]
    password: t.Optional[str] = field(repr=False)
    host: t.Optional[str]
    database: t.Optional[str]
    port: t.Optional[int] = 5432

    def __post_init__(self):
        if (self.db_name == "sqlite") and (self.database is None):
            raise ValueError(
                "A sqlite connection requires a path to a *.db file "
                "through the `database` argument"
            )

    @property
    def connection(self):
        if self.db_name == "postgresql":
            return self._make_psycopg_connection
        elif self.db_name == "mysql":
            return self._make_mysql_connection
        elif self.db_name == "sqlite":
            return self._make_sqlite_connection
        raise ValueError(f"Unsupported database {self.db_name} connection.")

    def _make_sqlite_connection(self):
        from sqlite3 import connect

        return connect(database=self.database)

    @requires_dependencies(["psycopg2"])
    def _make_psycopg_connection(self):
        from psycopg2 import connect

        return connect(
            user=self.username,
            password=self.password,
            dbname=self.database,
            host=self.host,
            port=self.port,
        )

    @requires_dependencies(["mysql"])
    def _make_mysql_connection(self):
        import mysql.connector

        return mysql.connector.connect(
            user=self.username,
            password=self.password,
            database=self.database,
            host=self.host,
            port=self.port,
        )


@dataclass
class SqlWriteConfig(WriteConfig):
    mode: t.Literal["error", "append", "overwrite"] = "error"
    table_name_mapping: t.Optional[t.Dict[str, str]] = None
    table_column_mapping: t.Optional[t.Dict[str, str]] = None

    def __post_init__(self):
        if self.table_column_mapping is None:
            self.table_name_mapping = {
                ELEMENTS_TABLE_NAME: ELEMENTS_TABLE_NAME,
                METADATA_TABLE_NAME: METADATA_TABLE_NAME,
                DATA_SOURCE_TABLE_NAME: DATA_SOURCE_TABLE_NAME,
                COORDINATES_TABLE_NAME: COORDINATES_TABLE_NAME,
            }
        if self.table_column_mapping is None:
            self.table_column_mapping = {}


@dataclass
class SqlDestinationConnector(BaseDestinationConnector):
    write_config: SqlWriteConfig
    connector_config: SimpleSqlConfig

    def initialize(self):
        pass

    def check_connection(self):
        return self.connector_config.connection()

    def conform_dict(self, data: dict) -> tuple:
        """
        Updates the element dictionary to conform to the sql schema
        """
        from datetime import datetime

        data["id"] = str(uuid.uuid4())
        data["metadata_id"] = None
        if data.get("metadata"):
            metadata_id = str(uuid.uuid4())
            data["metadata"]["id"] = metadata_id
            data["metadata_id"] = metadata_id
            data["data_source_id"] = None
            data["coordinates_id"] = None

            if data.get("metadata", {}).get("data_source"):
                data_source_id = str(uuid.uuid4())
                data["metadata"]["data_source"]["id"] = data_source_id
                data["data_source_id"] = data_source_id

            if data.get("metadata", {}).get("coordinates"):
                coordinates_id = str(uuid.uuid4())
                data["metadata"]["coordinates"]["id"] = coordinates_id
                data["coordinates_id"] = coordinates_id

        # Dict as string formatting
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            # Explicit casting otherwise fails schema type checking
            data["metadata"]["data_source"]["record_locator"] = str(json.dumps(record_locator))

        # Array of items as string formatting
        if (embeddings := data.get("embeddings")) and (
            self.connector_config.db_name != "postgresql"
        ):
            data["embeddings"] = str(json.dumps(embeddings))

        if points := data.get("metadata", {}).get("coordinates", {}).get("points"):
            data["metadata"]["coordinates"]["points"] = str(json.dumps(points))

        if links := data.get("metadata", {}).get("links", {}):
            data["metadata"]["links"] = str(json.dumps(links))

        if permissions_data := (
            data.get("metadata", {}).get("data_source", {}).get("permissions_data")
        ):
            data["metadata"]["data_source"]["permissions_data"] = json.dumps(permissions_data)

        if link_texts := data.get("metadata", {}).get("link_texts", {}):
            data["metadata"]["link_texts"] = str(json.dumps(link_texts))

        if sent_from := data.get("metadata", {}).get("sent_from", {}):
            data["metadata"]["sent_from"] = str(json.dumps(sent_from))

        if sent_to := data.get("metadata", {}).get("sent_to", {}):
            data["metadata"]["sent_to"] = str(json.dumps(sent_to))

        if emphasized_text_contents := data.get("metadata", {}).get("emphasized_text_contents", {}):
            data["metadata"]["emphasized_text_contents"] = str(json.dumps(emphasized_text_contents))

        # Datetime formatting
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = datetime.fromisoformat(date_created)

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = datetime.fromisoformat(date_modified)

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = datetime.fromisoformat(
                date_processed
            )

        if last_modified := data.get("metadata", {}).get("last_modified", {}):
            data["metadata"]["last_modified"] = datetime.fromisoformat(last_modified)

        # String casting
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)

        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = str(json.dumps(regex_metadata))

        data_source = data.get("metadata", {}).pop("data_source", None)
        coordinates = data.get("metadata", {}).pop("coordinates", None)
        metadata = data.pop("metadata", None)

        return data, metadata, data_source, coordinates

    def _resolve_mode(self, schema_exists) -> t.Optional[dict]:
        if self.write_config.mode == "error" and schema_exists:
            raise ValueError(
                f"There's already an elements schema ({str(self.write_config.table_name_mapping)}) "
                f"at {self.connector_config.db_url}"
            )

    # @DestinationConnectionError.wrap
    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} objects to database {self.connector_config.database} "
            f"at {self.connector_config.host}"
        )

        conn = self.connector_config.connection()
        with conn:
            schema_helper = DatabaseSchema(conn=conn, db_name=self.connector_config.db_name)

            schema_exists = schema_helper.check_schema_exists(self.write_config.table_name_mapping)
            self._resolve_mode(schema_exists)
            for e in json_list:
                elem, mdata, dsource, coords = self.conform_dict(e)
                if coords is not None:
                    coords_name = self.write_config.table_name_mapping[COORDINATES_TABLE_NAME]
                    schema_helper.insert(
                        coords_name, coords, self.write_config.table_column_mapping.get(coords_name)
                    )

                if dsource is not None:
                    dsource_name = self.write_config.table_name_mapping[DATA_SOURCE_TABLE_NAME]
                    schema_helper.insert(
                        coords_name,
                        dsource,
                        self.write_config.table_column_mapping.get(dsource_name),
                    )

                if mdata is not None:
                    mdata_name = self.write_config.table_name_mapping[METADATA_TABLE_NAME]
                    schema_helper.insert(
                        mdata_name,
                        mdata,
                        self.write_config.table_column_mapping.get(mdata_name),
                    )

                elements_name = self.write_config.table_name_mapping[ELEMENTS_TABLE_NAME]
                schema_helper.insert(
                    elements_name,
                    elem,
                    self.write_config.table_column_mapping.get(elements_name),
                )

            conn.commit()
        conn.close()

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                json_content = json.load(json_file)
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        self.write_dict(json_list=json_list)
