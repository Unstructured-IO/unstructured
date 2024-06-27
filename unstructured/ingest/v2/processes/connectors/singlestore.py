import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd
from dateutil import parser

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.ingest.utils.table import convert_to_pandas_dataframe
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    FileData,
    UploadContent,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)

if TYPE_CHECKING:
    from singlestoredb.connection import Connection

CONNECTOR_TYPE = "singlestore"


@dataclass
class SingleStoreAccessConfig(AccessConfig):
    password: Optional[str] = None


@dataclass
class SingleStoreConnectionConfig(ConnectionConfig):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    database: Optional[str] = None
    access_config: SingleStoreAccessConfig = enhanced_field(sensitive=True)

    def get_connection(self) -> "Connection":
        import singlestoredb as s2

        conn = s2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.access_config.password,
        )
        return conn


@dataclass
class SingleStoreUploadStagerConfig(UploadStagerConfig):
    drop_empty_cols: bool = True


@dataclass
class SingleStoreUploadStager(UploadStager):
    upload_stager_config: SingleStoreUploadStagerConfig

    @staticmethod
    def parse_date_string(date_string: str) -> date:
        try:
            timestamp = float(date_string)
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.debug(f"date {date_string} string not a timestamp: {e}")
        return parser.parse(date_string)

    def conform_dict(self, data: dict) -> None:
        """
        Updates the element dictionary to conform to the sql schema
        """

        data["id"] = str(uuid.uuid4())

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

        if sent_from := data.get("metadata", {}).get("sent_from", {}):
            data["metadata"]["sent_from"] = str(json.dumps(sent_from))

        if sent_to := data.get("metadata", {}).get("sent_to", {}):
            data["metadata"]["sent_to"] = str(json.dumps(sent_to))

        # Datetime formatting
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = self.parse_date_string(date_created)

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = self.parse_date_string(date_modified)

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = self.parse_date_string(
                date_processed
            )

        if last_modified := data.get("metadata", {}).get("last_modified", {}):
            data["metadata"]["last_modified"] = self.parse_date_string(last_modified)

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

    def run(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents = json.load(elements_file)
        # for element in elements_contents:
        #     self.conform_dict(data=element)
        output_path = Path(output_dir) / Path(f"{output_filename}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = convert_to_pandas_dataframe(
            elements_dict=elements_contents,
            drop_empty_cols=self.upload_stager_config.drop_empty_cols,
        )
        with output_path.open("w") as output_file:
            df.to_csv(output_file, index=False)
        return output_path


@dataclass
class SingleStoreUploaderConfig(UploaderConfig):
    table_name: str
    batch_size: int = 100


@dataclass
class SingleStoreUploader(Uploader):
    connection_config: SingleStoreConnectionConfig
    upload_config: SingleStoreUploaderConfig
    connector_type: str = CONNECTOR_TYPE

    def upload_csv(self, content: UploadContent) -> None:
        df = pd.read_csv(content.path)
        logger.debug(
            f"uploading {len(df)} entries to {self.connection_config.database} "
            f"db in table {self.upload_config.table_name}"
        )
        stmt = "INSERT INTO {} VALUES ({})".format(
            self.upload_config.table_name, ", ".join(["%s"] * len(df.columns))
        )
        logger.debug(f"sql statement: {stmt}")
        df.replace({np.nan: None}, inplace=True)
        data_as_tuples = list(df.itertuples(index=False, name=None))
        with self.connection_config.get_connection() as conn:
            with conn.cursor() as cur:
                for chunk in chunk_generator(
                    data_as_tuples, batch_size=self.upload_config.batch_size
                ):
                    # cur.executemany(stmt, chunk)
                    # conn.commit()
                    for c in chunk:
                        try:
                            cur.execute(stmt, c)
                            conn.commit()
                        except Exception as e:
                            for i, cc in enumerate(df.columns):
                                print(f"{cc}: {type(c[i])} {c[i]}")
                            logger.error(f"failed to write entry: {c}")
                            raise e

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        for content in contents:
            self.upload_csv(content=content)


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=SingleStoreConnectionConfig,
        uploader=SingleStoreUploader,
        uploader_config=SingleStoreUploaderConfig,
        upload_stager=SingleStoreUploadStager,
        upload_stager_config=SingleStoreUploadStagerConfig,
    ),
)
