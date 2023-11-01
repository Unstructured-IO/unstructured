import io
import json
import os
import typing as t
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSourceConnector,
    DatabricksVolumesConfig,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


@dataclass
class SimpleDatabricksVolumesConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    auth_configs: dict
    volume_configs: DatabricksVolumesConfig


@dataclass
class DatabricksVolumesIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleDatabricksVolumesConfig
    registry_name: str = "databricks_volumes"

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        pass

    @property
    def _output_filename(self):
        pass

    @property
    def version(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks")
    def get_file(self):
        pass

    def convert_datetime(self, date_time):
        for format in DATE_FORMATS:
            try:
                return datetime.strptime(date_time, format).timestamp()
            except ValueError:
                pass

    @property
    def filename(self):
        return self._tmp_download_file()


@requires_dependencies(dependencies=["databricks.sdk"], extras="databricks")
class DatabricksVolumesSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleDatabricksVolumesConfig

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks")
    def __post_init__(self):
        from databricks.sdk import WorkspaceClient

        self.workspace = WorkspaceClient(**self.connector_config.auth_configs)

    def get_ingest_docs(self):
        return []


@dataclass
class DatabricksVolumesWriteConfig(WriteConfig):
    overwrite: bool = False


@dataclass
class DatabricksVolumesDestinationConnector(BaseDestinationConnector):
    write_config: DatabricksVolumesWriteConfig
    connector_config: SimpleDatabricksVolumesConfig

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks")
    def __post_init__(self):
        from databricks.sdk import WorkspaceClient

        self.workspace = WorkspaceClient(**self.connector_config.auth_configs)

    def initialize(self):
        pass

    def write_dict(
        self,
        *args,
        json_list: t.List[t.Dict[str, t.Any]],
        filename: t.Optional[str] = None,
        indent: int = 4,
        encoding: str = "utf-8",
        **kwargs,
    ) -> None:
        output_folder = self.connector_config.volume_configs.remote_url
        output_folder = os.path.join(output_folder)  # Make sure folder ends with file seperator
        filename = (
            filename.strip(os.sep) if filename else filename
        )  # Make sure filename doesn't begin with file seperator
        output_path = str(PurePath(output_folder, filename)) if filename else output_folder
        logger.debug(f"uploading content to {output_path}")
        encoded_data = json.dumps(json_list, indent=indent).encode(encoding=encoding)
        self.workspace.files.upload(
            file_path=output_path,
            overwrite=self.write_config.overwrite,
            contents=io.BytesIO(encoded_data),
        )

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databrsicks")
    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        for doc in docs:
            file_path = doc.base_output_filename
            filename = file_path if file_path else None
            with open(doc._output_filename) as json_file:
                logger.debug(f"uploading content from {doc._output_filename}")
                json_list = json.load(json_file)
                self.write_dict(json_list=json_list, filename=filename)
