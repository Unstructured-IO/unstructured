import json
import multiprocessing as mp
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

import pandas as pd
from dateutil import parser

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import WriteError
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
)
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from pymilvus import MilvusClient

CONNECTOR_TYPE = "milvus"


@dataclass
class MilvusAccessConfig(AccessConfig):
    password: Optional[str] = None
    token: Optional[str] = None


@dataclass
class MilvusConnectionConfig(ConnectionConfig):
    access_config: MilvusAccessConfig = enhanced_field(
        sensitive=True, default_factory=lambda: MilvusAccessConfig()
    )
    uri: Optional[str] = None
    user: Optional[str] = None
    db_name: Optional[str] = None

    def get_connection_kwargs(self) -> dict[str, Any]:
        access_config_dict = self.access_config.to_dict()
        connection_config_dict = self.to_dict()
        connection_config_dict.pop("access_config", None)
        connection_config_dict.update(access_config_dict)
        # Drop any that were not set explicitly
        connection_config_dict = {k: v for k, v in connection_config_dict.items() if v is not None}
        return connection_config_dict

    @requires_dependencies(["pymilvus"], extras="milvus")
    def get_client(self) -> "MilvusClient":
        from pymilvus import MilvusClient

        return MilvusClient(**self.get_connection_kwargs())


@dataclass
class MilvusUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class MilvusUploadStager(UploadStager):
    upload_stager_config: MilvusUploadStagerConfig = field(
        default_factory=lambda: MilvusUploadStagerConfig()
    )

    @staticmethod
    def parse_date_string(date_string: str) -> float:
        try:
            timestamp = float(date_string)
            return timestamp
        except ValueError:
            pass
        return parser.parse(date_string).timestamp()

    @classmethod
    def conform_dict(cls, data: dict) -> None:
        datetime_columns = [
            "data_source_date_created",
            "data_source_date_modified",
            "data_source_date_processed",
            "last_modified",
        ]

        json_dumps_fields = ["languages", "data_source_permissions_data"]

        # TODO: milvus sdk doesn't seem to support defaults via the schema yet,
        #  remove once that gets updated
        defaults = {"is_continuation": False}

        if metadata := data.pop("metadata", None):
            data.update(flatten_dict(metadata, keys_to_omit=["data_source_record_locator"]))
        for datetime_column in datetime_columns:
            if datetime_column in data:
                data[datetime_column] = cls.parse_date_string(data[datetime_column])
        for json_dumps_field in json_dumps_fields:
            if json_dumps_field in data:
                data[json_dumps_field] = json.dumps(data[json_dumps_field])
        for default in defaults:
            if default not in data:
                data[default] = defaults[default]

    def run(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents: list[dict[str, Any]] = json.load(elements_file)
        for element in elements_contents:
            self.conform_dict(data=element)

        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as output_file:
            json.dump(elements_contents, output_file, indent=2)
        return output_path


@dataclass
class MilvusUploaderConfig(UploaderConfig):
    collection_name: str
    num_of_processes: int = 4


@dataclass
class MilvusUploader(Uploader):
    connection_config: MilvusConnectionConfig
    upload_config: MilvusUploaderConfig
    connector_type: str = CONNECTOR_TYPE

    def upload(self, content: UploadContent) -> None:
        file_extension = content.path.suffix
        if file_extension == ".json":
            self.upload_json(content=content)
        elif file_extension == ".csv":
            self.upload_csv(content=content)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

    @requires_dependencies(["pymilvus"], extras="milvus")
    def insert_results(self, data: Union[dict, list[dict]]):
        from pymilvus import MilvusException

        logger.debug(
            f"uploading {len(data)} entries to {self.connection_config.db_name} "
            f"db in collection {self.upload_config.collection_name}"
        )
        client = self.connection_config.get_client()

        try:
            res = client.insert(collection_name=self.upload_config.collection_name, data=data)
        except MilvusException as milvus_exception:
            raise WriteError("failed to upload records to milvus") from milvus_exception
        if "err_count" in res and isinstance(res["err_count"], int) and res["err_count"] > 0:
            err_count = res["err_count"]
            raise WriteError(f"failed to upload {err_count} docs")

    def upload_csv(self, content: UploadContent) -> None:
        df = pd.read_csv(content.path)
        data = df.to_dict(orient="records")
        self.insert_results(data=data)

    def upload_json(self, content: UploadContent) -> None:
        with content.path.open("r") as file:
            data: list[dict] = json.load(file)
        self.insert_results(data=data)

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        if self.upload_config.num_of_processes == 1:
            for content in contents:
                self.upload_csv(content=content)

        else:
            with mp.Pool(
                processes=self.upload_config.num_of_processes,
            ) as pool:
                pool.map(self.upload, contents)


milvus_destination_entry = DestinationRegistryEntry(
    connection_config=MilvusConnectionConfig,
    uploader=MilvusUploader,
    uploader_config=MilvusUploaderConfig,
    upload_stager=MilvusUploadStager,
    upload_stager_config=MilvusUploadStagerConfig,
)
