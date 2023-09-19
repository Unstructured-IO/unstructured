import json
import typing as t
from dataclasses import dataclass

import azure.core.exceptions

from unstructured.ingest.error import WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleAzureCognitiveSearchStorageConfig(BaseConnectorConfig):
    endpoint: str
    key: str


@dataclass
class AzureCognitiveSearchWriteConfig(WriteConfig):
    index: str


@dataclass
class AzureCognitiveSearchDestinationConnector(BaseDestinationConnector):
    write_config: AzureCognitiveSearchWriteConfig
    connector_config: SimpleAzureCognitiveSearchStorageConfig

    @requires_dependencies(["azure"], extras="azure-cognitive-search")
    def initialize(self):
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        # Create a client
        credential = AzureKeyCredential(self.connector_config.key)
        self.client = SearchClient(
            endpoint=self.connector_config.endpoint,
            index_name=self.write_config.index,
            credential=credential,
        )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                # TODO figure out how to map to destination schema
                json_content = json.load(json_file)
                for content in json_content:
                    content["metadata"] = json.dumps(content["metadata"])
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        logger.info(
            f"writing {len(json_list)} documents to destination "
            f"index at {self.write_config.index}",
        )
        try:
            results = self.client.upload_documents(documents=json_list)

        except azure.core.exceptions.HttpResponseError as http_error:
            raise WriteError(f"http error: {http_error}") from http_error
        errors = []
        success = []
        for result in results:
            if result.succeeded:
                success.append(result)
            else:
                errors.append(result)
        logger.debug(f"results: {len(success)} successes, {len(errors)} failures")
        if errors:
            raise WriteError(
                ", ".join(
                    [
                        f"{error.key}: [{error.status_code}] {error.error_message}"
                        for error in errors
                    ],
                ),
            )
