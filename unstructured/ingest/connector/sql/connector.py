import json
import typing as t
import uuid
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
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
    ELEMENTS_TABLE_NAME,
    DatabaseSchema,
)


@dataclass
class SqlAccessConfig(AccessConfig):
    username: t.Optional[str]
    password: t.Optional[str] = enhanced_field(sensitive=True)


@dataclass
class SimpleSqlConfig(BaseConnectorConfig):
    db_type: t.Optional[str]
    host: t.Optional[str]
    database: t.Optional[str]
    port: t.Optional[int]
    access_config: SqlAccessConfig

    def __post_init__(self):
        if (self.db_type == "sqlite") and (self.database is None):
            raise ValueError(
                "A sqlite connection requires a path to a *.db file "
                "through the `database` argument"
            )

    @property
    def connection(self):
        if self.db_type == "postgresql":
            return self._make_psycopg_connection
        elif self.db_type == "sqlite":
            return self._make_sqlite_connection
        raise ValueError(f"Unsupported database {self.db_type} connection.")

    def _make_sqlite_connection(self):
        from sqlite3 import connect

        return connect(database=self.database)

    @requires_dependencies(["psycopg2"], extras="postgresql")
    def _make_psycopg_connection(self):
        from psycopg2 import connect

        return connect(
            user=self.access_config.username,
            password=self.access_config.password,
            dbname=self.database,
            host=self.host,
            port=self.port,
        )


@dataclass
class SqlWriteConfig(WriteConfig):
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error"


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

    @DestinationConnectionError.wrap
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

        # Dict as string formatting
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            # Explicit casting otherwise fails schema type checking
            data["metadata"]["data_source"]["record_locator"] = str(json.dumps(record_locator))

        # Array of items as string formatting
        if (embeddings := data.get("embeddings")) and (
            self.connector_config.db_type != "postgresql"
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

        if data.get("metadata", {}).get("data_source", None):
            data.update(data.get("metadata", {}).pop("data_source", None))
        if data.get("metadata", {}).get("coordinates", None):
            data.update(data.get("metadata", {}).pop("coordinates", None))
        if data.get("metadata", {}):
            data.update(data.pop("metadata", None))

        return data

    def check_mode(self, schema_helper: DatabaseSchema) -> t.Optional[dict]:
        schema_exists = schema_helper.check_schema_exists()
        if schema_exists:
            if self.write_config.mode == "error":
                raise ValueError(
                    f"There's already an elements schema ({ELEMENTS_TABLE_NAME}) "
                    f"at {self.connector_config.db_type}"
                )
            elif self.write_config.mode == "ignore":
                logger.info("Table already exists. Ignoring insert.")
                return False
            elif self.write_config.mode == "overwrite":
                logger.info("Table already exists. Clearing table.")
                schema_helper.clear_schema()
                return True
            elif self.write_config.mode == "append":
                logger.info("Table already exists. Appending to table.")
                return True
        else:
            return True

    @DestinationConnectionError.wrap
    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} objects to database {self.connector_config.database} "
            f"at {self.connector_config.host}"
        )

        with self.client as conn:
            schema_helper = DatabaseSchema(
                conn=conn,
                db_type=self.connector_config.db_type,
            )

            # Prep table and insert elements depending on mode
            if self.check_mode(schema_helper):
                for e in json_list:
                    elem = self.conform_dict(e)

                    schema_helper.insert(
                        ELEMENTS_TABLE_NAME,
                        elem,
                    )

                conn.commit()
                schema_helper.cursor.close()

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
