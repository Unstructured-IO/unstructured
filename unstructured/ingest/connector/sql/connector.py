import json
import typing as t
import uuid
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.interfaces import (
    AccessConfig,
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
class SqlAccessConfig(AccessConfig):
    password: t.Optional[str] = enhanced_field(sensitive=True)


@dataclass
class SimpleSqlConfig(BaseConnectorConfig):
    db_name: t.Optional[str]
    username: t.Optional[str]
    # password: t.Optional[str] = field(repr=False)
    host: t.Optional[str]
    database: t.Optional[str]
    port: t.Optional[int]
    access_config: SqlAccessConfig

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
        elif self.db_name == "sqlite":
            return self._make_sqlite_connection
        raise ValueError(f"Unsupported database {self.db_name} connection.")

    def _make_sqlite_connection(self):
        from sqlite3 import connect

        return connect(database=self.database)

    @requires_dependencies(["psycopg2"], extras="postgresql")
    def _make_psycopg_connection(self):
        from psycopg2 import connect

        return connect(
            user=self.username,
            password=self.access_config.password,
            dbname=self.database,
            host=self.host,
            port=self.port,
        )


@dataclass
class SqlWriteConfig(WriteConfig):
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error"
    table_name_mapping: t.Optional[t.Dict[str, str]] = None
    table_column_mapping: t.Optional[t.Dict[str, str]] = None

    def __post_init__(self):
        if self.table_name_mapping is None:
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
    _client: t.Optional[t.Any] = field(init=False, default=None)

    @property
    def client(self):
        if self._client is None:
            self._client = self.connector_config.connection()
        return self._client

    def initialize(self):
        _ = self.client

    def check_connection(self):
        cursor = self.client.cursor()
        cursor.execute("SELECT 1;")
        cursor.close()

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

    def _resolve_mode(self, schema_helper: DatabaseSchema) -> t.Optional[dict]:
        schema_exists = schema_helper.check_schema_exists()
        if (
            self.write_config.mode == "error" or self.write_config.mode == "ignore"
        ) and schema_exists:
            breakpoint()
            raise ValueError(
                f"There's already an elements schema ({str(self.write_config.table_name_mapping)}) "
                f"at {self.connector_config.db_name}"
            )
        if self.write_config.mode == "overwrite" and schema_exists:
            schema_helper.clear_schema()

    # @DestinationConnectionError.wrap
    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} objects to database {self.connector_config.database} "
            f"at {self.connector_config.host}"
        )

        with self.client as conn:
            schema_helper = DatabaseSchema(
                conn=conn,
                db_name=self.connector_config.db_name,
                table_name_mapping=self.write_config.table_name_mapping,
                table_column_mapping=self.write_config.table_column_mapping,
            )

            self._resolve_mode(schema_helper)
            for e in json_list:
                elem, mdata, dsource, coords = self.conform_dict(e)
                if coords is not None:
                    schema_helper.insert(
                        COORDINATES_TABLE_NAME,
                        self.write_config.table_name_mapping[COORDINATES_TABLE_NAME],
                        coords,
                    )

                if dsource is not None:
                    schema_helper.insert(
                        DATA_SOURCE_TABLE_NAME,
                        self.write_config.table_name_mapping[DATA_SOURCE_TABLE_NAME],
                        dsource,
                    )

                if mdata is not None:
                    schema_helper.insert(
                        METADATA_TABLE_NAME,
                        self.write_config.table_name_mapping[METADATA_TABLE_NAME],
                        mdata,
                    )

                schema_helper.insert(
                    ELEMENTS_TABLE_NAME,
                    self.write_config.table_name_mapping[ELEMENTS_TABLE_NAME],
                    elem,
                )

            conn.commit()
            schema_helper.cursor.close()
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
