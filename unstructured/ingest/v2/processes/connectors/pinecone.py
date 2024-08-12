import json
import multiprocessing as mp
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.utils.data_prep import batch_generator
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
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
    from pinecone import Index as PineconeIndex


CONNECTOR_TYPE = "pinecone"


@dataclass
class PineconeAccessConfig(AccessConfig):
    api_key: Optional[str] = enhanced_field(default=None, overload_name="pinecone_api_key")


@dataclass
class PineconeConnectionConfig(ConnectionConfig):
    index_name: str
    environment: str
    access_config: PineconeAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["pinecone"], extras="pinecone")
    def get_index(self) -> "PineconeIndex":
        from pinecone import Pinecone

        from unstructured import __version__ as unstructured_version

        pc = Pinecone(
            api_key=self.access_config.api_key,
            source_tag=f"unstructured=={unstructured_version}",
        )

        index = pc.Index(self.index_name)
        logger.debug(f"Connected to index: {pc.describe_index(self.index_name)}")
        return index


@dataclass
class PineconeUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class PineconeUploaderConfig(UploaderConfig):
    batch_size: int = 100
    num_of_processes: int = 4


@dataclass
class PineconeUploadStager(UploadStager):
    upload_stager_config: PineconeUploadStagerConfig = field(
        default_factory=lambda: PineconeUploadStagerConfig()
    )

    @staticmethod
    def conform_dict(element_dict: dict) -> dict:
        # While flatten_dict enables indexing on various fields,
        # element_serialized enables easily reloading the element object to memory.
        # element_serialized is formed without text/embeddings to avoid data bloating.
        return {
            "id": str(uuid.uuid4()),
            "values": element_dict.pop("embeddings", None),
            "metadata": {
                "text": element_dict.pop("text", None),
                "element_serialized": json.dumps(element_dict),
                **flatten_dict(
                    element_dict,
                    separator="-",
                    flatten_lists=True,
                    remove_none=True,
                ),
            },
        }

    def run(
        self,
        elements_filepath: Path,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents = json.load(elements_file)

        conformed_elements = [
            self.conform_dict(element_dict=element) for element in elements_contents
        ]

        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as output_file:
            json.dump(conformed_elements, output_file)
        return output_path


@dataclass
class PineconeUploader(Uploader):
    upload_config: PineconeUploaderConfig
    connection_config: PineconeConnectionConfig
    connector_type: str = CONNECTOR_TYPE

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.connection_config.get_index()

    @requires_dependencies(["pinecone"], extras="pinecone")
    def upsert_batch(self, batch):
        from pinecone.exceptions import PineconeApiException

        try:
            index = self.connection_config.get_index()
            response = index.upsert(batch)
        except PineconeApiException as api_error:
            raise DestinationConnectionError(f"http error: {api_error}") from api_error
        logger.debug(f"results: {response}")

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:

        elements_dict = []
        for content in contents:
            with open(content.path) as elements_file:
                elements = json.load(elements_file)
                elements_dict.extend(elements)

        logger.info(
            f"writing document batches to destination"
            f" index named {self.connection_config.index_name}"
            f" environment named {self.connection_config.environment}"
            f" with batch size {self.upload_config.batch_size}"
            f" with {self.upload_config.num_of_processes} (number of) processes"
        )

        pinecone_batch_size = self.upload_config.batch_size

        if self.upload_config.num_of_processes == 1:
            for batch in batch_generator(elements_dict, pinecone_batch_size):
                self.upsert_batch(batch)  # noqa: E203

        else:
            with mp.Pool(
                processes=self.upload_config.num_of_processes,
            ) as pool:
                pool.map(
                    self.upsert_batch, list(batch_generator(elements_dict, pinecone_batch_size))
                )


pinecone_destination_entry = DestinationRegistryEntry(
    connection_config=PineconeConnectionConfig,
    uploader=PineconeUploader,
    uploader_config=PineconeUploaderConfig,
    upload_stager=PineconeUploadStager,
    upload_stager_config=PineconeUploadStagerConfig,
)
