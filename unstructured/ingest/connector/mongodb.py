import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from dataclasses_json.core import Json

from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from pymongo import MongoClient


SERVER_API_VERSION = "1"


def parse_userinfo(userinfo: str) -> t.Tuple[str, str]:
    user, _, passwd = userinfo.partition(":")
    return user, passwd


def redact(uri: str, redacted_text="***REDACTED***") -> str:
    """
    Cherry pick code from pymongo.uri_parser.parse_uri to only extract password and
    redact without needing to import pymongo library
    """

    SCHEME = "mongodb://"
    SRV_SCHEME = "mongodb+srv://"
    if uri.startswith(SCHEME):
        scheme_free = uri[len(SCHEME) :]  # noqa: E203
    elif uri.startswith(SRV_SCHEME):
        scheme_free = uri[len(SRV_SCHEME) :]  # noqa: E203
    else:
        raise ValueError(f"Invalid URI scheme: URI must begin with '{SCHEME}' or '{SRV_SCHEME}'")

    passwd = None

    host_part, _, path_part = scheme_free.partition("/")
    if not host_part:
        host_part = path_part
        path_part = ""

    if not path_part:
        # There was no slash in scheme_free, check for a sole "?".
        host_part, _, _ = host_part.partition("?")

    if "@" in host_part:
        userinfo, _, hosts = host_part.rpartition("@")
        _, passwd = parse_userinfo(userinfo)

    if passwd:
        uri = uri.replace(passwd, redacted_text)
    return uri


# MongoDBAccessConfig here SKIPPING due to uri

# -----------------------------------

#### Think about versioning


@dataclass
class SimpleMongoDBConfig(BaseConnectorConfig):
    uri: t.Optional[str] = None
    host: t.Optional[str] = None
    database: t.Optional[str] = None
    collection: t.Optional[str] = None
    port: int = 27017

    def to_dict(
        self, redact_sensitive=False, redacted_text="***REDACTED***", **kwargs
    ) -> t.Dict[str, Json]:
        d = super().to_dict(
            redact_sensitive=redact_sensitive, redacted_text=redacted_text, **kwargs
        )
        if redact_sensitive:
            if self.host:
                d["host"] = redact(uri=self.host, redacted_text=redacted_text)
            if self.uri:
                d["uri"] = redact(uri=self.uri, redacted_text=redacted_text)
        return d


@dataclass
class MongoDBDocumentMeta:
    collection: str
    document_id: str


@dataclass
class MongoDBIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleMongoDBConfig
    document_meta: MongoDBDocumentMeta
    document: dict = field(default_factory=dict)
    registry_name: str = "mongodb"

    @property
    def filename(self):
        f = self.document_meta.document_id
        # breakpoint()
        # if self.connector_config.fields:
        #     f = "{}-{}".format(
        #         f,
        #         hashlib.sha256(",".join(self.connector_config.fields).encode()).hexdigest()[:8],
        #     )
        return (
            Path(self.read_config.download_dir) / self.document_meta.collection / f"{f}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        # Generate SHA256 hash and take the first 8 characters
        filename = self.document_meta.document_id
        # if self.connector_config.fields:
        #     filename = "{}-{}".format(
        #         filename,
        #         hashlib.sha256(",".join(self.connector_config.fields).encode()).hexdigest()[:8],
        #     )
        output_file = f"{filename}.json"
        return (
            Path(self.processor_config.output_dir) / self.connector_config.collection / output_file
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["pymongo"], extras="mongodb")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        pass


@dataclass
class MongoDBSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleMongoDBConfig
    _client: t.Optional["MongoClient"] = field(init=False, default=None)

    @requires_dependencies(["pymongo"], extras="mongodb")
    def generate_client(self) -> "MongoClient":
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        if self.connector_config.uri:
            return MongoClient(
                self.connector_config.uri, server_api=ServerApi(version=SERVER_API_VERSION)
            )
        else:
            return MongoClient(
                host=self.connector_config.host,
                port=self.connector_config.port,
                server_api=ServerApi(version=SERVER_API_VERSION),
            )

    @property
    def client(self) -> "MongoClient":
        if self._client is None:
            self._client = self.generate_client()
        return self._client

    def get_collection(self):
        database = self.client[self.connector_config.database]
        return database.get_collection(name=self.connector_config.collection)

    def check_connection(self):
        try:
            self.client.admin.command("ping")
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def initialize(self):
        _ = self.client

    def _get_doc_ids(self):
        """Fetches all document ids in a collection. actually returns ObjectId"""
        collection = self.get_collection()
        return collection.distinct("_id")

    def get_ingest_docs(self) -> t.List[BaseSingleIngestDoc]:
        collection = self.get_collection()
        ids = self._get_doc_ids()
        ingest_docs = []
        for doc_id in ids:
            # breakpoint()
            doc = collection.find_one({"_id": doc_id})
            ingest_doc = MongoDBIngestDoc(
                processor_config=self.processor_config,
                read_config=self.read_config,
                connector_config=self.connector_config,
                document_meta=MongoDBDocumentMeta(
                    collection=self.connector_config.collection, document_id=doc_id
                ),
                document=doc,
                # check for read_config, processor_config
            )
            # ingest_doc.update_source_metadata()
            del doc["_id"]
            filename = ingest_doc.filename
            flattened_dict = flatten_dict(dictionary=doc)
            str_values = [str(value) for value in flattened_dict.values()]
            concatenated_values = "\n".join(str_values)

            filename.parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "w", encoding="utf8") as f:
                f.write(concatenated_values)

            ingest_docs.append(ingest_doc)
        return ingest_docs


# _get_doc_ids

# get_ingest_docs
# initialize
# check_connection


##### Write from here on down.


@dataclass
class MongoDBWriteConfig(WriteConfig):
    pass
    # database: str
    # collection: str


@dataclass
class MongoDBDestinationConnector(BaseDestinationConnector):
    # write_config: MongoDBWriteConfig
    connector_config: SimpleMongoDBConfig
    _client: t.Optional["MongoClient"] = field(init=False, default=None)

    @requires_dependencies(["pymongo"], extras="mongodb")
    def generate_client(self) -> "MongoClient":
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        if self.connector_config.uri:
            return MongoClient(
                self.connector_config.uri, server_api=ServerApi(version=SERVER_API_VERSION)
            )
        else:
            return MongoClient(
                host=self.connector_config.host,
                port=self.connector_config.port,
                server_api=ServerApi(version=SERVER_API_VERSION),
            )

    @property
    def client(self) -> "MongoClient":
        if self._client is None:
            self._client = self.generate_client()
        return self._client

    @requires_dependencies(["pymongo"], extras="mongodb")
    def check_connection(self):
        try:
            self.client.admin.command("ping")
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def initialize(self):
        _ = self.client

    def get_collection(self):
        database = self.client[self.connector_config.database]
        return database.get_collection(name=self.connector_config.collection)

    @requires_dependencies(["pymongo"], extras="mongodb")
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(elements_dict)} documents to destination "
            f"database {self.connector_config.database}, at collection {self.connector_config.collection}",
        )

        collection = self.get_collection()
        try:
            collection.insert_many(elements_dict)
        except Exception as e:
            logger.error(f"failed to write records: {e}", exc_info=True)
            raise WriteError(f"failed to write records: {e}")
