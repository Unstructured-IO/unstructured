import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies

USER_AGENT = "mixedbread-ai@unstructured"

if TYPE_CHECKING:
    from mixedbread_ai.client import MixedbreadAI
    from mixedbread_ai.core import RequestOptions


@dataclass
class MixedBreadAIEmbeddingConfig(EmbeddingConfig):
    """
    Configuration class for Mixedbread AI Embedding Encoder.

    Attributes:
        api_key (str): API key for accessing Mixedbread AI.
        base_url (Optional[str]): Base URL for the API.
        timeout (Optional[int]): Timeout for API requests in seconds.
        max_retries (Optional[int]): Maximum number of retries for API requests.
        batch_size (Optional[int]): Batch size of API requests.
        model_name (str): Name of the model to use for embeddings.
        normalized (bool): Whether to normalize the embeddings.
        encoding_format (Optional[EncodingFormat]): Format of the encoding.
        truncation_strategy (Optional[TruncationStrategy]): Strategy for truncating text.
        dimensions (Optional[int]): Number of dimensions for the embeddings.
        prompt (Optional[str]): Optional prompt for embedding generation.
    """

    from mixedbread_ai import EncodingFormat, TruncationStrategy

    api_key: str = field(
        default_factory=lambda: os.environ.get("MXBAI_API_KEY", None),
    )
    base_url: Optional[str] = field(default=None)
    timeout: Optional[int] = field(default=60)
    max_retries: Optional[int] = field(default=3)
    batch_size: Optional[int] = field(default=128)

    model_name: str = field(
        default="mixedbread-ai/mxbai-embed-large-v1",
    )
    normalized: bool = field(default=True)
    encoding_format: Optional["EncodingFormat"] = field(
        default=EncodingFormat.FLOAT,
    )
    truncation_strategy: Optional["TruncationStrategy"] = field(default=TruncationStrategy.START)
    dimensions: Optional[int] = field(default=None)
    prompt: Optional[str] = field(default=None)


@dataclass
class MixedbreadAIEmbeddingEncoder(BaseEmbeddingEncoder):
    """
    Embedding encoder for Mixedbread AI.

    Attributes:
        config (MixedBreadAIEmbeddingConfig): Configuration for the embedding encoder.
    """

    config: MixedBreadAIEmbeddingConfig

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
                "The mixedbread ai API key must be specified."
                + "You either pass it in the constructor using 'api_key'"
                + "or via the 'MXBAI_API_KEY' environment variable."
            )

        if self.config.timeout is not None and self.config.timeout <= 0:
            raise ValueError("The timeout parameter must be greater than 0.")
        if self.config.max_retries is not None and self.config.max_retries < 0:
            raise ValueError("The max_retries parameter must be greater than or equal to 0.")

        if self.config.batch_size is not None and self.config.batch_size <= 0:
            raise ValueError("The batch_size parameter must be greater than 0.")

        from mixedbread_ai.core import RequestOptions

        self._request_options = RequestOptions(
            max_retries=self.config.max_retries,
            timeout_in_seconds=self.config.timeout,
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
        batch_size = self.config.batch_size or len(texts)
        batch_itr = range(0, len(texts), batch_size)

        responses = []

        for i in batch_itr:
            batch = texts[i : i + batch_size]
            response = self.client.embeddings(
                model=self.config.model_name,
                normalized=self.config.normalized,
                encoding_format=self.config.encoding_format,
                truncation_strategy=self.config.truncation_strategy,
                dimensions=self.config.dimensions,
                prompt=self.config.prompt,
                request_options=self._request_options,
                input=batch,
            )
            responses.append(response)
        return [item.embedding for response in responses for item in response.data]

    @staticmethod
    def _add_embeddings_to_elements(elements, embeddings) -> List[Element]:
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
    @requires_dependencies(["mixedbread_ai"])
    def create_client(self) -> "MixedbreadAI":
        """
        Create the Mixedbread AI client.

        Returns:
            MixedbreadAI: Initialized client.
        """
        from mixedbread_ai.client import MixedbreadAI

        return MixedbreadAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )
