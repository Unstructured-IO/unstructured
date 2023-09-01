import os
from dataclasses import dataclass
from datetime import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import pandas as pd

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from deltalake import DeltaTable


@dataclass
class SimpleDeltaTableConfig(BaseConnectorConfig):
    verbose: bool
    table_uri: Union[str, Path]
    version: Optional[int] = None
    storage_options: Optional[Dict[str, str]] = None
    without_files: bool = False
    columns: Optional[List[str]] = None


@dataclass
class DeltaTableIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleDeltaTableConfig
    uri: str
    modified_date: str
    created_at: str
    registry_name: str = "delta-table"

    def uri_filename(self) -> str:
        basename = os.path.basename(self.uri)
        return os.path.splitext(basename)[0]

    @property
    def source_url(self) -> Optional[str]:
        """The url of the source document."""
        return self.uri

    @property
    def date_created(self) -> Optional[str]:
        """This is the creation time of the table itself, not the file or specific record"""
        # TODO get creation time of file/record
        return self.created_at

    @property
    def filename(self):
        return (Path(self.standard_config.download_dir) / f"{self.uri_filename()}.csv").resolve()

    @property
    def date_modified(self) -> Optional[str]:
        """The date the document was last modified on the source system."""
        return self.modified_date

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        return Path(self.standard_config.output_dir) / f"{self.uri_filename()}.json"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self._output_filename.parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["fsspec"], extras="delta-table")
    def get_file(self):
        import pyarrow.parquet as pq
        from fsspec.core import url_to_fs

        try:
            fs, _ = url_to_fs(self.uri)
        except ImportError as error:
            raise ImportError(
                f"uri {self.uri} may be associated with a filesystem that "
                f"requires additional dependencies: {error}",
            )
        logger.info(f"using a {fs} filesystem to collect table data")
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        df: pd.DataFrame = pq.ParquetDataset(self.uri, filesystem=fs).read_pandas().to_pandas()

        logger.info(f"writing {len(df)} rows to {self.filename}")
        df.to_csv(self.filename)


@dataclass
class DeltaTableConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleDeltaTableConfig
    delta_table: Optional["DeltaTable"] = None

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleDeltaTableConfig,
    ):
        super().__init__(standard_config, config)

    @requires_dependencies(["deltalake"], extras="delta-table")
    def initialize(self):
        from deltalake import DeltaTable

        self.delta_table = DeltaTable(
            table_uri=self.config.table_uri,
            version=self.config.version,
            storage_options=self.config.storage_options,
            without_files=self.config.without_files,
        )
        rows = self.delta_table.to_pyarrow_dataset().count_rows()
        if not rows > 0:
            raise ValueError(f"no data found at {self.config.table_uri}")
        logger.info(f"processing {rows} rows of data")

    def get_ingest_docs(self):
        """Batches the results into distinct docs"""
        if not self.delta_table:
            raise ValueError("delta table was never initialized")
        actions = self.delta_table.get_add_actions().to_pandas()
        mod_date_dict = {
            row["path"]: str(row["modification_time"]) for _, row in actions.iterrows()
        }
        created_at = dt.fromtimestamp(self.delta_table.metadata().created_time / 1000)
        return [
            DeltaTableIngestDoc(
                standard_config=self.standard_config,
                config=self.config,
                uri=uri,
                modified_date=mod_date_dict[os.path.basename(uri)],
                created_at=str(created_at),
            )
            for uri in self.delta_table.file_uris()
        ]
