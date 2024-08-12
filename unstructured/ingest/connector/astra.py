import copy
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured import __name__ as integration_name
from unstructured.__version__ import __version__ as integration_version
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import batch_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from astrapy.db import AstraDB, AstraDBCollection

NON_INDEXED_FIELDS = ["metadata._node_content", "content"]


@dataclass
class AstraAccessConfig(AccessConfig):
    token: str = enhanced_field(sensitive=True)
    api_endpoint: str = enhanced_field(sensitive=True)


@dataclass
class SimpleAstraConfig(BaseConnectorConfig):
    access_config: AstraAccessConfig
    collection_name: str
    namespace: t.Optional[str] = None


@dataclass
class AstraIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleAstraConfig
    metadata: t.Dict[str, str] = field(default_factory=dict)
    registry_name: str = "astra"

    @property
    def filename(self):
        return (
            Path(self.read_config.download_dir)
            / self.connector_config.collection_name
            / f"{self.metadata['_id']}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        return (
            Path(self.processor_config.output_dir)
            / self.connector_config.collection_name
            / f"{self.metadata['_id']}.json"
        ).resolve()

    def update_source_metadata(self, **kwargs):
        if not self.metadata:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            exists=True,
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["astrapy"], extras="astra")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        flattened_dict = flatten_dict(dictionary=self.metadata)
        str_values = [str(value) for value in flattened_dict.values()]
        concatenated_values = "\n".join(str_values)

        with open(self.filename, "w") as f:
            f.write(concatenated_values)


@dataclass
class AstraSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleAstraConfig
    _astra_db: t.Optional["AstraDB"] = field(init=False, default=None)
    _astra_db_collection: t.Optional["AstraDBCollection"] = field(init=False, default=None)

    @property
    @requires_dependencies(["astrapy"], extras="astra")
    def astra_db_collection(self) -> "AstraDBCollection":
        if self._astra_db_collection is None:
            from astrapy.db import AstraDB

            # Build the Astra DB object.
            # caller_name/version for AstraDB tracking
            self._astra_db = AstraDB(
                api_endpoint=self.connector_config.access_config.api_endpoint,
                token=self.connector_config.access_config.token,
                namespace=self.connector_config.namespace,
                caller_name=integration_name,
                caller_version=integration_version,
            )

            # Create and connect to the collection
            self._astra_db_collection = self._astra_db.collection(
                collection_name=self.connector_config.collection_name,
            )
        return self._astra_db_collection  # type: ignore

    @requires_dependencies(["astrapy"], extras="astra")
    @SourceConnectionError.wrap  # type: ignore
    def initialize(self):
        _ = self.astra_db_collection

    @requires_dependencies(["astrapy"], extras="astra")
    def check_connection(self):
        try:
            _ = self.astra_db_collection
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    @requires_dependencies(["astrapy"], extras="astra")
    def get_ingest_docs(self):  # type: ignore
        # Perform the find operation
        astra_docs = list(self.astra_db_collection.paginated_find())

        doc_list = []
        for record in astra_docs:
            doc = AstraIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                metadata=record,
            )

            doc.update_source_metadata()

            doc_list.append(doc)

        return doc_list


@dataclass
class AstraWriteConfig(WriteConfig):
    embedding_dimension: int
    requested_indexing_policy: t.Optional[t.Dict[str, t.Any]] = None
    batch_size: int = 20


@dataclass
class AstraDestinationConnector(BaseDestinationConnector):
    write_config: AstraWriteConfig
    connector_config: SimpleAstraConfig
    _astra_db: t.Optional["AstraDB"] = field(init=False, default=None)
    _astra_db_collection: t.Optional["AstraDBCollection"] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        """
        The _astra_db_collection variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)

        if hasattr(self_cp, "_astra_db_collection"):
            setattr(self_cp, "_astra_db_collection", None)

        return _asdict(self_cp, **kwargs)

    @property
    @requires_dependencies(["astrapy"], extras="astra")
    def astra_db_collection(self) -> "AstraDBCollection":
        if self._astra_db_collection is None:
            from astrapy.db import AstraDB

            collection_name = self.connector_config.collection_name
            embedding_dimension = self.write_config.embedding_dimension

            # If the user has requested an indexing policy, pass it to the AstraDB
            requested_indexing_policy = self.write_config.requested_indexing_policy
            options = {"indexing": requested_indexing_policy} if requested_indexing_policy else None

            # caller_name/version for AstraDB tracking
            self._astra_db = AstraDB(
                api_endpoint=self.connector_config.access_config.api_endpoint,
                token=self.connector_config.access_config.token,
                namespace=self.connector_config.namespace,
                caller_name=integration_name,
                caller_version=integration_version,
            )

            # Create and connect to the newly created collection
            self._astra_db_collection = self._astra_db.create_collection(
                collection_name=collection_name,
                dimension=embedding_dimension,
                options=options,
            )
        return self._astra_db_collection

    @requires_dependencies(["astrapy"], extras="astra")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.astra_db_collection

    @requires_dependencies(["astrapy"], extras="astra")
    def check_connection(self):
        try:
            _ = self.astra_db_collection
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(elements_dict)} documents to Astra.")

        astra_batch_size = self.write_config.batch_size

        for batch in batch_generator(elements_dict, astra_batch_size):
            self._astra_db_collection.insert_many(batch)

    def normalize_dict(self, element_dict: dict) -> dict:
        return {
            "$vector": element_dict.pop("embeddings", None),
            "content": element_dict.pop("text", None),
            "metadata": element_dict,
        }
