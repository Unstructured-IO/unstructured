from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, List, Optional, cast

import numpy as np
from pydantic import Field, SecretStr

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from voyageai import Client

DEFAULT_VOYAGE_2_BATCH_SIZE = 72
DEFAULT_VOYAGE_3_LITE_BATCH_SIZE = 30
DEFAULT_VOYAGE_3_BATCH_SIZE = 10
DEFAULT_BATCH_SIZE = 7


class VoyageAIEmbeddingConfig(EmbeddingConfig):
    api_key: SecretStr
    model_name: str
    show_progress_bar: bool = False
    batch_size: Optional[int] = Field(default=None)
    truncation: Optional[bool] = Field(default=None)
    output_dimension: Optional[int] = Field(default=None)

    @requires_dependencies(
        ["voyageai"],
        extras="embed-voyageai",
    )
    def get_client(self) -> "Client":
        """Creates a VoyageAI python client to embed elements."""
        from voyageai import Client

        return Client(
            api_key=self.api_key.get_secret_value(),
        )

    def get_batch_size(self):
        if self.batch_size is None:
            if self.model_name in ["voyage-2", "voyage-02"]:
                self.batch_size = DEFAULT_VOYAGE_2_BATCH_SIZE
            elif self.model_name == "voyage-3-lite":
                self.batch_size = DEFAULT_VOYAGE_3_LITE_BATCH_SIZE
            elif self.model_name == "voyage-3":
                self.batch_size = DEFAULT_VOYAGE_3_BATCH_SIZE
            else:
                self.batch_size = DEFAULT_BATCH_SIZE
        return self.batch_size


@dataclass
class VoyageAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: VoyageAIEmbeddingConfig

    def get_exemplary_embedding(self) -> List[float]:
        return self.embed_query(query="A sample query.")

    def initialize(self):
        pass

    @property
    def num_of_dimensions(self) -> tuple[int, ...]:
        exemplary_embedding = self.get_exemplary_embedding()
        return np.shape(exemplary_embedding)

    @property
    def is_unit_vector(self) -> bool:
        exemplary_embedding = self.get_exemplary_embedding()
        return np.isclose(np.linalg.norm(exemplary_embedding), 1.0)

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        client = self.config.get_client()
        embeddings: List[List[float]] = []

        _iter = self._get_batch_iterator(elements)
        for i in _iter:
            r = client.embed(
                texts=[str(e) for e in elements[i : i + self.config.get_batch_size()]],
                model=self.config.model_name,
                input_type="document",
                truncation=self.config.truncation,
                output_dimension=self.config.output_dimension,
            ).embeddings
            embeddings.extend(cast(Iterable[List[float]], r))
        return self._add_embeddings_to_elements(elements, embeddings)

    def embed_query(self, query: str) -> List[float]:
        client = self.config.get_client()
        return client.embed(
            texts=[query],
            model=self.config.model_name,
            input_type="query",
            truncation=self.config.truncation,
            output_dimension=self.config.output_dimension,
        ).embeddings[0]

    @staticmethod
    def _add_embeddings_to_elements(elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        elements_w_embedding = []
        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements

    def _get_batch_iterator(self, elements: List[Element]) -> Iterable:
        if self.config.show_progress_bar:
            try:
                from tqdm.auto import tqdm  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "Must have tqdm installed if `show_progress_bar` is set to True. "
                    "Please install with `pip install tqdm`."
                ) from e

            _iter = tqdm(range(0, len(elements), self.config.get_batch_size()))
        else:
            _iter = range(0, len(elements), self.config.get_batch_size())  # type: ignore

        return _iter
