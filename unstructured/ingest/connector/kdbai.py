import copy
import typing as t
import pandas as pd
import uuid
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from kdbai_client import Table


@dataclass
class KDBAIAccessConfig(AccessConfig):
    api_key: str = enhanced_field(sensitive=True)


@dataclass
class SimpleKDBAIConfig(BaseConnectorConfig):
    access_config: KDBAIAccessConfig
    table_name: str
    endpoint: t.Optional[str] = None


@dataclass
class KDBAIWriteConfig(WriteConfig):
    batch_size: int = 100


@dataclass
class KDBAIDestinationConnector(BaseDestinationConnector):
    write_config: KDBAIWriteConfig
    connector_config: SimpleKDBAIConfig
    _table: t.Optional["Table"] = None

    @property
    def KDBAI_table(self):
        if self._table is None:
            self._table = self.create_table()
        return self._table

    def initialize(self):
        pass

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.KDBAI_table

    def to_dict(self, **kwargs):
        """
        The _collection variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle 'module' object
        When serializing, remove it, meaning collection data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_collection"):
            setattr(self_cp, "_collection", None)
        return _asdict(self_cp, **kwargs)

    @requires_dependencies(["kdbai_client"], extras="kdbai")
    def create_table(self) -> "Table":
        import kdbai_client as kdbai

        try:
            session = kdbai.Session(
                endpoint=self.connector_config.endpoint,
                api_key=self.connector_config.access_config.api_key,
            )
        except Exception as e:
            raise ValueError(f"KDBAI error: {e}") from e

        if self.connector_config.table_name in session.list():
            table = session.table(self.connector_config.table_name)
        else:
            # Set the schema of the table
            pass

        logger.debug(
            f"Connected to table: {self.connector_config.table_name}"
        )
        return table

    @DestinationConnectionError.wrap
    @requires_dependencies(["kdbai_client"], extras="kdbai")
    def upsert_batch(self, batch):
        table = self.KDBAI_table

        try:
            table.insert(batch)
        except Exception as e:
            raise ValueError(f"KDBAI error: {e}") from e

    @staticmethod
    def prepare_kdbai_dataframe(chunk: t.Tuple[t.Dict[str, t.Any]]) -> pd.DataFrame:
        """
        Helper function to convert a tuple of dicts into a pandas DataFrame.
        ({'id':1}, {'id':2}, {'id':3}) -> DataFrame with columns 'id', 'document', 'embedding', 'metadata'
        """
        import pandas as pd

        data = []
        for d in chunk:
            data.append({
                'id': d.get('id'),
                'document': d.get('document'),
                'embedding': d.get('embedding'),
                'metadata': d.get('metadata')
            })
        
        df = pd.DataFrame(data)

        assert (len(df['id']) == len(df['document']) == len(df['embedding']) == len(df['metadata']))
        
        return df
    
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting {len(elements_dict)} elements to destination "
            f"index at {self.connector_config.table_name}",
        )

        kdbai_batch_size = self.write_config.batch_size

        for chunk in chunk_generator(elements_dict, kdbai_batch_size):
            self.upsert_batch(self.prepare_kdbai_dataframe(chunk))

    def normalize_dict(self, element_dict: dict) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "document": element_dict.pop("text", None),
            "embedding": element_dict.pop("embeddings", None),
            "metadata": flatten_dict(
                element_dict, separator="-", flatten_lists=True, remove_none=True
            ),
        }
