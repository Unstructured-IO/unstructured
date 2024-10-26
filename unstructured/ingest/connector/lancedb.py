import copy
import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import batch_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    import lancedb

@dataclass
class LanceDBAccessConfig(AccessConfig):
    uri: str = enhanced_field(sensitive=True)

@dataclass
class SimpleLanceDBConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    table_name: str
    access_config: LanceDBAccessConfig

@dataclass
class LanceDBWriteConfig(WriteConfig):
    batch_size: int = 50
    num_processes: int = 1

@dataclass
class LanceDBDestinationConnector(IngestDocSessionHandleMixin, BaseDestinationConnector):
    write_config: LanceDBWriteConfig
    connector_config: SimpleLanceDBConfig
    _table: t.Optional["lancedb.Table"] = None

    def to_dict(self, **kwargs):
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_table"):
            setattr(self_cp, "_table", None)
        return _asdict(self_cp, **kwargs)

    @property
    def lancedb_table(self):
        if self._table is None:
            self._table = self.create_table()
        return self._table

    def initialize(self):
        pass

    @requires_dependencies(["lancedb"], extras="lancedb")
    def create_table(self) -> "lancedb.Table":
        import lancedb

        db = lancedb.connect(self.connector_config.access_config.uri)
        table = db.open_table(self.connector_config.table_name)
        logger.debug(f"Connected to table: {table}")
        return table

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.lancedb_table

    @DestinationConnectionError.wrap
    @requires_dependencies(["lancedb"], extras="lancedb")
    def add_batch(self, batch):
        table = self.lancedb_table
        try:
            table.add(batch)
        except Exception as error:
            raise WriteError(f"LanceDB error: {error}") from error
        logger.debug(f"Added {len(batch)} records to the table")

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Adding {len(elements_dict)} elements to destination "
            f"table {self.connector_config.table_name}",
        )

        lancedb_batch_size = self.write_config.batch_size

        logger.info(f"using {self.write_config.num_processes} processes to upload")
        if self.write_config.num_processes == 1:
            for chunk in batch_generator(elements_dict, lancedb_batch_size):
                self.add_batch(chunk)

        else:
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                pool.map(
                    self.add_batch, list(batch_generator(elements_dict, lancedb_batch_size))
                )

    def normalize_dict(self, element_dict: dict) -> dict:
        flattened = flatten_dict(
            element_dict,
            separator="_",
            flatten_lists=True,
            remove_none=True,
        )
        return {
            "id": str(uuid.uuid4()),
            "vector": flattened.pop("embeddings", None),
            "text": flattened.pop("text", None),
            "metadata": json.dumps(flattened),
            **flattened,
        }