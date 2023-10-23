import json
import typing as t
from dataclasses import dataclass

import pinecone.core.client.exceptions

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimplePineconeConfig(BaseConnectorConfig):
    api_key: str
    index_name: str
    environment: str


@dataclass
class PineconeWriteConfig(WriteConfig):
    api_key: str
    index_name: str
    environment: str


# When upserting larger amounts of data, upsert data in batches of 100 vectors
# or fewer over multiple upsert requests.
@dataclass
class PineconeDestinationConnector(BaseDestinationConnector):
    write_config: WriteConfig
    connector_config: SimplePineconeConfig

    @DestinationConnectionError.wrap
    @requires_dependencies(["pinecone"], extras="pinecone")
    def initialize(self):
        import pinecone

        pinecone.init(
            api_key=self.connector_config.api_key,
            environment=self.connector_config.environment,
        )

        self.index = pinecone.Index(self.connector_config.index_name)

        print("Connected to index:", pinecone.describe_index(self.connector_config.index_name))

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting / updating {len(dict_list)} documents to destination "
            f"index at {self.connector_config.index_name}",
        )
        for i in range(0, len(dict_list), 100):
            try:
                response = self.index.upsert(dict_list[i : i + 100])  # noqa: E203
            except pinecone.core.client.exceptions.ApiException as api_error:
                raise WriteError(f"http error: {api_error}") from api_error
            logger.debug(f"results: {response}")

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []

        import shutil
        import zipfile
        from pathlib import Path

        output_dir = Path(str(docs[0]._output_filename).lstrip("/").split("/")[0])
        old_dir = output_dir / "small-pdf-set"
        embeddings_zip = output_dir / "small-pdf-set.zip"

        shutil.rmtree(old_dir)

        # make sure you made a .zip file for the embeddings output first
        with zipfile.ZipFile(embeddings_zip, "r") as zip_ref:
            zip_ref.extractall(output_dir)

        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)

                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                dict_content = [
                    {
                        "id": element.pop("element_id", None),
                        "values": element.pop("embeddings", None),
                        "metadata": {k: json.dumps(v) for k, v in element.items()},
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"appending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
        self.write_dict(dict_list=dict_list)
