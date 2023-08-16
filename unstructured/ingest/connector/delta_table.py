import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas
import pyarrow
from deltalake import DeltaTable
from pyarrow import RecordBatch

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import make_default_logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleDeltaTableConfig(BaseConnectorConfig):
    verbose: bool
    table_uri: Union[str, Path]
    version: Optional[int] = None
    storage_options: Optional[Dict[str, str]] = None
    without_files: bool = False
    columns: Optional[List[str]] = None
    batch_size: Optional[int] = None
    logger: Optional[logging.Logger] = None

    def get_logger(self) -> logging.Logger:
        if self.logger:
            return self.logger
        return make_default_logger(logging.DEBUG if self.verbose else logging.INFO)

    def get_batch_kwargs(self) -> Dict[str, Any]:
        to_batches_kwargs: Dict[str, Any] = {}
        if self.columns:
            to_batches_kwargs["columns"] = self.columns
        if self.batch_size:
            to_batches_kwargs["batch_size"] = self.batch_size
        return to_batches_kwargs


@dataclass
class DeltaTableIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleDeltaTableConfig
    batch: RecordBatch
    _id: Optional[uuid.UUID] = None

    @property
    def id(self):
        if not self._id:
            self._id = uuid.uuid4()
        return self._id

    @property
    def filename(self):
        return (Path(self.standard_config.download_dir) / f"{self.id}.csv").resolve()

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        return Path(self.standard_config.output_dir) / f"{self.id}.json"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self._output_filename.parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(["elasticsearch"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        self._create_full_tmp_dir_path()
        self.config.get_logger().debug(f"Fetching {self} - PID: {os.getpid()}")

        df: pandas.DataFrame = self.batch.to_pandas()
        self.config.get_logger().info(f"writing {len(df)} rows to {self.filename}")
        df.to_csv(self.filename)


@requires_dependencies(["deltalake"])
@dataclass
class DeltaTableConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleDeltaTableConfig
    delta_table: Optional[DeltaTable] = None

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleDeltaTableConfig,
    ):
        super().__init__(standard_config, config)

    def initialize(self):
        self.delta_table = DeltaTable(
            table_uri=self.config.table_uri,
            version=self.config.version,
            storage_options=self.config.storage_options,
            without_files=self.config.without_files,
        )
        rows = self.delta_table.to_pyarrow_dataset().count_rows()
        if not rows > 0:
            raise ValueError(f"no data found at {self.config.table_uri}")
        self.config.get_logger().info(f"processing {rows} rows of data")

    def get_ingest_docs(self):
        """Batches the results into distinct docs"""
        if not self.delta_table:
            raise ValueError("delta table was never initialized")
        dataset: pyarrow.dataset.Dataset = self.delta_table.to_pyarrow_dataset()
        return [
            DeltaTableIngestDoc(
                standard_config=self.standard_config,
                config=self.config,
                batch=batch,
            )
            for batch in dataset.to_batches(**self.config.get_batch_kwargs())
        ]
