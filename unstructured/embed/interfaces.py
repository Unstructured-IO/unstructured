from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple

from pydantic import BaseModel

from unstructured.documents.elements import Element


class EmbeddingConfig(BaseModel):
    pass


@dataclass
class BaseEmbeddingEncoder(ABC):
    config: EmbeddingConfig

    @abstractmethod
    def initialize(self):
        """Initializes the embedding encoder class. Should also validate the instance
        is properly configured: e.g., embed a single a element"""

    @property
    @abstractmethod
    def num_of_dimensions(self) -> Tuple[int]:
        """Number of dimensions for the embedding vector."""

    @property
    @abstractmethod
    def is_unit_vector(self) -> bool:
        """Denotes if the embedding vector is a unit vector."""

    @abstractmethod
    def embed_documents(self, elements: List[Element]) -> List[Element]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass
