import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies

USER_AGENT = "@mixedbread-ai/unstructured"
BATCH_SIZE = 128
TIMEOUT = 60
MAX_RETRIES = 3
ENCODING_FORMAT = "float"
TRUNCATION_STRATEGY = "end"


if TYPE_CHECKING:
    from mixedbread_ai.client import MixedbreadAI
    from mixedbread_ai.core import RequestOptions


@dataclass
class MixedbreadAIEmbeddingConfig(EmbeddingConfig):
    """
    Configuration class for Mixedbread AI Embedding Encoder.

    Attributes:
        api_key (str): API key for accessing Mixedbread AI..
        model_name (str): Name of the model to use for embeddings.
    """

    api_key: str = field(
        default_factory=lambda: os.environ.get("MXBAI_API_KEY"),
    )

    model_name: str = field(
        default="mixedbread-ai/mxbai-embed-large-v1",
    )


@dataclass
class MixedbreadAIEmbeddingEncoder(BaseEmbeddingEncoder):
    """
    Embedding encoder for Mixedbread AI.

    Attributes:
        config (MixedbreadAIEmbeddingConfig): Configuration for the embedding encoder.
    """

    config: MixedbreadAIEmbeddingConfig

    _client: Optional["MixedbreadAI"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)
    _request_options: Optional["RequestOptions"] = field(init=False, default=None)

    @property
    def client(self) -> "MixedbreadAI":
        """Lazy initialization of the Mixedbread AI client."""
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        """Get an exemplary embedding to determine dimensions and unit vector status."""
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self._embed(["Q"])[0]
        return self._exemplary_embedding

    def initialize(self):
        if self.config.api_key is None:
            raise ValueError(
                "The Mixedbread AI API key must be specified."
                + "You either pass it in the constructor using 'api_key'"
                + "or via the 'MXBAI_API_KEY' environment variable."
            )

        from mixedbread_ai.core import RequestOptions

        self._request_options = RequestOptions(
            max_retries=MAX_RETRIES,
            timeout_in_seconds=TIMEOUT,
            additional_headers={"User-Agent": USER_AGENT},
        )

    @property
    def num_of_dimensions(self):
        """Get the number of dimensions for the embeddings."""
        return np.shape(self.exemplary_embedding)

    @property
    def is_unit_vector(self) -> bool:
        """Check if the embedding is a unit vector."""
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts using the Mixedbread AI API.

        Args:
            texts (List[str]): List of texts to embed.

        Returns:
            List[List[float]]: List of embeddings.
        """
        batch_size = BATCH_SIZE
        batch_itr = range(0, len(texts), batch_size)

        responses = []

        for i in batch_itr:
            batch = texts[i : i + batch_size]
            response = self.client.embeddings(
                model=self.config.model_name,
                normalized=True,
                encoding_format=ENCODING_FORMAT,
                truncation_strategy=TRUNCATION_STRATEGY,
                request_options=self._request_options,
                input=batch,
            )
            responses.append(response)
        return [item.embedding for response in responses for item in response.data]

    @staticmethod
    def _add_embeddings_to_elements(
        elements: List[Element], embeddings: List[List[float]]
    ) -> List[Element]:
        """
        Add embeddings to elements.

        Args:
            elements (List[Element]): List of elements.
            embeddings (List[List[float]]): List of embeddings.

        Returns:
            List[Element]: Elements with embeddings added.
        """
        assert len(elements) == len(embeddings)
        elements_w_embedding = []
        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        """
        Embed a list of document elements.

        Args:
            elements (List[Element]): List of document elements.

        Returns:
            List[Element]: Elements with embeddings.
        """
        embeddings = self._embed([str(e) for e in elements])
        return self._add_embeddings_to_elements(elements, embeddings)

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query string.

        Args:
            query (str): Query string to embed.

        Returns:
            List[float]: Embedding of the query.
        """
        return self._embed([query])[0]

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["mixedbread_ai"],
        extras="embed-mixedbreadai",
    )
    def create_client(self) -> "MixedbreadAI":
        """
        Create the Mixedbread AI client.

        Returns:
            MixedbreadAI: Initialized client.
        """
        from mixedbread_ai.client import MixedbreadAI

        return MixedbreadAI(
            api_key=self.config.api_key,
        )
