from abc import ABC, abstractmethod
from typing import List, Optional

from unstructured.documents.elements import Element


class BaseEmbeddingEncoder(ABC):
    @abstractmethod
    def initialize():
        """Initializes the embedding encoder class. Should also validate the instance
        is properly configured: e.g., embed a single a element"""
        pass

    @property
    def num_of_dimensions(self) -> int:
        """Number of dimensions for the embedding vector."""
        return None

    @property
    def is_unit_vector(self) -> bool:
        """Denotes if the embedding vector is a unit vector."""
        return None

    @abstractmethod
    def embed(self, filename: Optional[str], elements: Optional[List[Element]]) -> List[Element]:
        pass
