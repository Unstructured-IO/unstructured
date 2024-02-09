import copy
import json
import typing as t
import uuid
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

ELEMENTS_TABLE_NAME = "elements"


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

    @requires_dependencies(["psycopg2"], extras="postgres")
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
class SqlDestinationConnector(BaseDestinationConnector):
    connector_config: SimpleSqlConfig
    _client: t.Optional[t.Any] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        """
        The _client variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_client"):
            setattr(self_cp, "_client", None)
        return _asdict(self_cp, **kwargs)

    @property
    def client(self):
        if self._client is None:
            self._client = self.connector_config.connection()
        return self._client

    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.client

    def check_connection(self):
        try:
            cursor = self.client.cursor()
            cursor.execute("SELECT 1;")
            cursor.close()
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def conform_dict(self, data: dict) -> None:
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

    @DestinationConnectionError.wrap
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(elements_dict)} objects to database {self.connector_config.database} "
            f"at {self.connector_config.host}"
        )

        with self.client as conn:
            cursor = conn.cursor()

            # Since we have no guarantee that each element will have the same keys
            # we insert each element individually
            for elem in elements_dict:
                query = f"INSERT INTO {ELEMENTS_TABLE_NAME} ({','.join(elem.keys())}) \
                VALUES({','.join(['?' if self.connector_config.db_type=='sqlite' else '%s' for x in elem])})"  # noqa E501
                values = []
                for v in elem.values():
                    if self.connector_config.db_type == "sqlite" and isinstance(v, list):
                        values.append(json.dumps(v))
                    else:
                        values.append(v)
                cursor.execute(query, values)

            conn.commit()
            cursor.close()

        # Leaving contexts doesn't close the connection, so doing it here
        conn.close()
