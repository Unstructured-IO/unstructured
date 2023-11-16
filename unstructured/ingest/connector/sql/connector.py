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

from .tables import (
    COORDINATES_TABLE_NAME,
    DATA_SOURCE_TABLE_NAME,
    ELEMENTS_TABLE_NAME,
    METADATA_TABLE_NAME,
    check_schema_exists,
    create_schema,
    drop_schema,
    make_schema,
)


@dataclass
class SimpleSqlConfig(BaseConnectorConfig):
    drivername: t.Optional[str]
    username: t.Optional[str]
    password: t.Optional[str] = field(repr=False)
    host: t.Optional[str]
    database: t.Optional[str]
    database_url: t.Optional[str] = None
    port: t.Optional[int] = 5432

    @property
    def db_url(self):
        from sqlalchemy.engine.url import URL

        if self.database_url is not None:
            return self.database_url

        return URL.create(
            drivername=self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


@dataclass
class SqlWriteConfig(WriteConfig):
    mode: t.Literal["error", "append", "overwrite"] = "error"
    table_name_mapping: t.Optional[t.Dict[str, str]] = None


@dataclass
class SqlDestinationConnector(BaseDestinationConnector):
    write_config: SqlWriteConfig
    connector_config: SimpleSqlConfig

    @requires_dependencies(["sqlalchemy"], extras="sql")
    def initialize(self):
        from sqlalchemy import create_engine

        self.engine = create_engine(self.connector_config.db_url)
        if self.write_config.table_name_mapping is None:
            self.write_config.table_name_mapping = {
                ELEMENTS_TABLE_NAME: ELEMENTS_TABLE_NAME,
                METADATA_TABLE_NAME: METADATA_TABLE_NAME,
                DATA_SOURCE_TABLE_NAME: DATA_SOURCE_TABLE_NAME,
                COORDINATES_TABLE_NAME: COORDINATES_TABLE_NAME,
            }

    def check_connection(self):
        pass

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
        if embeddings := data.get("embeddings"):
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

    def _resolve_schema(self) -> t.Optional[dict]:
        schema_exists = check_schema_exists(self.engine, self.write_config.table_name_mapping)
        if not schema_exists:
            return create_schema(self.engine, self.write_config.table_name_mapping)

        if self.write_config.mode == "error":
            raise ValueError(
                f"There's already an elements schema ({str(self.write_config.table_name_mapping)}) "
                f"at {self.connector_config.db_url}"
            )
        elif self.write_config.mode == "overwrite":
            drop_schema(self.engine, self.write_config.table_name_mapping)
            return create_schema(self.engine, self.write_config.table_name_mapping)
        elif self.write_config.mode == "append":
            return make_schema(self.write_config.table_name_mapping, self.engine.dialect.__str__)

        return None

    # @DestinationConnectionError.wrap
    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        from sqlalchemy import insert

        logger.info(
            f"writing {len(json_list)} objects to database url " f"{self.connector_config.db_url} "
        )

        schema = self._resolve_schema()
        if schema is None:
            return

        with self.engine.connect() as conn:
            for e in json_list:
                elem, mdata, dsource, coords = self.conform_dict(e)
                if coords is not None:
                    conn.execute(insert(schema[COORDINATES_TABLE_NAME]), [coords])

                if dsource is not None:
                    conn.execute(insert(schema[DATA_SOURCE_TABLE_NAME]), [dsource])

                if mdata is not None:
                    conn.execute(insert(schema[METADATA_TABLE_NAME]), [mdata])
                conn.execute(insert(schema[ELEMENTS_TABLE_NAME]), [elem])
                conn.commit()

    @requires_dependencies(["sqlalchemy"], extras="sql")
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
