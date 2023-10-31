import typing as t
from dataclasses import dataclass
from datetime import datetime

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.utils import (
    requires_dependencies,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


@dataclass
class SimpleDatabricksVolumesConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    auth_configs: dict
    remote_url: str
    recursive: bool = False


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
    @requires_dependencies(dependencies=["databricks-sdk"], extras="databricks")
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


@requires_dependencies(dependencies=["databricks-sdk"], extras="databricks")
class DatabricksVolumesSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleDatabricksVolumesConfig

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""

    def get_ingest_docs(self):
        return []
