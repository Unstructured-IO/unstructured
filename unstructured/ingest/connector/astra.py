import copy
import json
import typing as t
from dataclasses import dataclass, field
from warnings import warn

from unstructured import __name__ as integration_name
from unstructured.__version__ import __version__ as integration_version
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionNetworkError
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
    from astrapy.db import AstraDB, AstraDBCollection


@dataclass
class AstraAccessConfig(AccessConfig):
    token: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    api_endpoint: t.Optional[str] = enhanced_field(default=None, sensitive=True)


@dataclass
class SimpleAstraConfig(BaseConnectorConfig):
    access_config: AstraAccessConfig
    collection_name: str
    embedding_dimension: int
    namespace: t.Optional[str] = None
    requested_indexing_policy: t.Optional[t.Dict[str, t.Any]] = None


@dataclass
class AstraWriteConfig(WriteConfig):
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
            from astrapy.api import APIRequestError
            from astrapy.db import AstraDB

            # Get the collection_name and embedding dimension
            collection_name = self.connector_config.collection_name
            embedding_dimension = self.connector_config.embedding_dimension
            requested_indexing_policy = self.connector_config.requested_indexing_policy

            if requested_indexing_policy is not None:
                _options = {"indexing": requested_indexing_policy}
            else:
                _options = None

            # Build the Astra DB object.
            # caller_name/version for AstraDB tracking
            self._astra_db = AstraDB(
                api_endpoint=self.connector_config.access_config.api_endpoint,
                token=self.connector_config.access_config.token,
                namespace=self.connector_config.namespace,
                caller_name=integration_name,
                caller_version=integration_version,
            )

            try:
                # Create and connect to the newly created collection
                self._astra_db_collection = self._astra_db.create_collection(
                    collection_name=collection_name,
                    dimension=embedding_dimension,
                    options=_options,
                )
            except APIRequestError:
                # possibly the collection is preexisting and has legacy
                # indexing settings: verify
                get_coll_response = self._astra_db.get_collections(options={"explain": True})
                collections = (get_coll_response["status"] or {}).get("collections") or []
                preexisting = [
                    collection
                    for collection in collections
                    if collection["name"] == self.connector_config.collection_name
                ]
                if preexisting:
                    pre_collection = preexisting[0]
                    # if it has no "indexing", it is a legacy collection;
                    # otherwise it's unexpected warn and proceed at user's risk
                    pre_col_options = pre_collection.get("options") or {}
                    if "indexing" not in pre_col_options:
                        warn(
                            (
                                f"Collection '{collection_name}' is detected as "
                                "having indexing turned on for all fields "
                                "(either created manually or by older versions "
                                "of this plugin). This implies stricter "
                                "limitations on the amount of text"
                                " each entry can store. Consider reindexing anew on a"
                                " fresh collection to be able to store longer texts."
                            ),
                            UserWarning,
                            stacklevel=2,
                        )
                        self._astra_db_collection = self._astra_db.collection(
                            collection_name=collection_name,
                        )
                    else:
                        options_json = json.dumps(pre_col_options["indexing"])
                        warn(
                            (
                                f"Collection '{collection_name}' has unexpected 'indexing'"
                                f" settings (options.indexing = {options_json})."
                                " This can result in odd behaviour when running "
                                " metadata filtering and/or unwarranted limitations"
                                " on storing long texts. Consider reindexing anew on a"
                                " fresh collection."
                            ),
                            UserWarning,
                            stacklevel=2,
                        )
                        self._astra_db_collection = self._astra_db.collection(
                            collection_name=collection_name,
                        )
                else:
                    # other exception
                    raise

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
            raise SourceConnectionNetworkError(f"failed to validate connection: {e}")

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(elements_dict)} documents to Astra.")

        astra_batch_size = self.write_config.batch_size

        for chunk in chunk_generator(elements_dict, astra_batch_size):
            self._astra_db_collection.insert_many(chunk)

    def normalize_dict(self, element_dict: dict) -> dict:
        return {
            "$vector": element_dict.pop("embeddings", None),
            "content": element_dict.pop("text", None),
            "metadata": flatten_dict(
                element_dict, separator="-", flatten_lists=True, remove_none=True
            ),
        }
