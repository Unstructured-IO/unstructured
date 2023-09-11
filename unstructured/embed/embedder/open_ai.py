import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dataclasses_json import DataClassJsonMixin

from unstructured.documents.elements import (
    Element,
)
from unstructured.ingest.error import EmbedderConnectionError
from unstructured.ingest.interfaces import (
    BaseSessionHandle,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
)
from unstructured.ingest.logger import logger
from unstructured.partition.json import partition_json
from unstructured.utils import requires_dependencies


@requires_dependencies(["langchain"])  # add extras="langchain" when it's added to the makefile
@dataclass
class OpenAISessionHandle(BaseSessionHandle):
    from langchain.embeddings.openai import OpenAIEmbeddings

    service: OpenAIEmbeddings


@EmbedderConnectionError.wrap
@requires_dependencies(["langchain"])  # add extras="langchain" when it's added to the makefile
def create_openai_object(api_key, model_name):
    """
    Creates an OpenAI object to embed elements.
    Args:
        api_key: API Key, generated for the user
        model_name: Model name for OpenAI

    Returns:
        OpenAI Embeddings object
    """
    from langchain.embeddings.openai import OpenAIEmbeddings

    embedder = OpenAIEmbeddings(
        openai_api_key=api_key,
        model=model_name,
    )

    _ = embedder.embed_query("We are testing authentication")
    return embedder


@dataclass
class OpenAIEmbedderConfig(ConfigSessionHandleMixin):
    def __init__(
        self,
        api_key: str,
        list_of_elements_json_paths: List[str],
        output_dir: str,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name if model_name is not None else "text-embedding-ada-002"
        self.list_of_elements_json_paths = list_of_elements_json_paths
        self.output_dir = output_dir

    def create_session_handle(
        self,
    ) -> OpenAISessionHandle:
        service = create_openai_object(self.api_key, self.model_name)
        return OpenAISessionHandle(service=service)


class ElementEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Element):
            return {
                "text": obj.text,
                "element_id": obj.id,
                "embedding": obj.embedding,
                "metadata": obj.metadata.to_dict(),
            }
        return super().default(obj)


@dataclass
class OpenAIEmbeddingsDoc(IngestDocSessionHandleMixin, DataClassJsonMixin):
    """Class encapsulating reading elements in a doc and writing the obtained embeddings."""

    config: OpenAIEmbedderConfig
    filename: str

    @property
    def _output_filename(self):
        """Create output file path."""
        output_file = f"{self.filename}_with_embeddings.json"

        return (Path(self.config.output_dir) / output_file).resolve()

    def get_elements_from_json(self) -> List[Element]:
        """Reads elements"""
        return partition_json(filename=self.filename)

    @requires_dependencies(["langchain"], extras="jira")
    def embed_and_write_result(self):
        logger.debug(f"Reading: {self} - PID: {os.getpid()}")

        elements = self.get_elements_from_json()
        embeddings = self.session_handle.service.embed_documents([str(e) for e in elements])
        self.elements = self.add_embeddings_to_elements(elements, embeddings)
        # import pdb; pdb.set_trace()
        self.write_result()

    def add_embeddings_to_elements(self, elements, embeddings):
        assert len(elements) == len(embeddings)

        for i in range(len(elements)):
            elements[i].embedding = embeddings[i]

        return elements

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        self._output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self._output_filename, "w", encoding="utf8") as output_f:
            json.dump(self.elements, output_f, ensure_ascii=False, indent=2, cls=ElementEncoder)
        print(f"Wrote {self._output_filename}")
        logger.info(f"Wrote {self._output_filename}")


class OpenAIEmbedder:
    config: OpenAIEmbedderConfig

    def __init__(
        self,
        config: OpenAIEmbedderConfig,
    ):
        self.config = config

    @requires_dependencies(["langchain"])  # add extras="langchain" when it's added to the makefile
    def initialize(self):
        """Verifies that a connection can be established to OpenAI.
        Sends one embedding request for verification."""
        _ = self.config.create_session_handle().service

    def get_embed_docs(self):
        """Reads all result files to embed them."""
        return [
            OpenAIEmbeddingsDoc(
                self.config,
                filename,
            )
            for filename in self.config.list_of_elements_json_paths.split()
        ]
