import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd
from dateutil import parser

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.utils.data_prep import batch_generator
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
from unstructured.utils import requires_dependencies

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

    @requires_dependencies(["singlestoredb"], extras="singlestore")
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
    drop_empty_cols: bool = False


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
        output_path = Path(output_dir) / Path(f"{output_filename}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = convert_to_pandas_dataframe(
            elements_dict=elements_contents,
            drop_empty_cols=self.upload_stager_config.drop_empty_cols,
        )
        datetime_columns = [
            "data_source_date_created",
            "data_source_date_modified",
            "data_source_date_processed",
        ]
        for column in filter(lambda x: x in df.columns, datetime_columns):
            df[column] = df[column].apply(self.parse_date_string)
        if "data_source_record_locator" in df.columns:
            df["data_source_record_locator"] = df["data_source_record_locator"].apply(
                lambda x: json.dumps(x) if x else None
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
        stmt = "INSERT INTO {} ({}) VALUES ({})".format(
            self.upload_config.table_name,
            ", ".join(df.columns),
            ", ".join(["%s"] * len(df.columns)),
        )
        logger.debug(f"sql statement: {stmt}")
        df.replace({np.nan: None}, inplace=True)
        data_as_tuples = list(df.itertuples(index=False, name=None))
        with self.connection_config.get_connection() as conn:
            with conn.cursor() as cur:
                for chunk in batch_generator(
                    data_as_tuples, batch_size=self.upload_config.batch_size
                ):
                    cur.executemany(stmt, chunk)
                    conn.commit()

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
