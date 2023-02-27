from __future__ import annotations

from abc import ABC
from typing import List, Optional

from unstructured.documents.elements import Element, NarrativeText


class Document(ABC):
    """The base class for all document types. A document consists of an ordered list of pages."""

    def __init__(self):
        self._pages: Optional[List[Page]] = None
        self._elements: Optional[List[Element]] = None

    def __str__(self) -> str:
        return "\n\n".join([str(page) for page in self.pages])

    def get_narrative(self) -> List[NarrativeText]:
        """Pulls out all of the narrative text sections from the document."""
        narrative: List[NarrativeText] = []
        for page in self.pages:
            for element in page.elements:
                if isinstance(element, NarrativeText):
                    narrative.append(element)
        return narrative

    @property
    def pages(self) -> List[Page]:
        """Gets all elements from pages in sequential order."""
        if self._pages is None:
            raise NotImplementedError(
                "When subclassing, _pages should always be populated before "
                "using the pages property.",
            )
        return self._pages

    @property
    def elements(self) -> List[Element]:
        """Gets all elements from pages in sequential order."""
        if self._elements is None:
            self._elements = [el for page in self.pages for el in page.elements]
        return self._elements

    def after_element(self, element: Element) -> Document:
        """Returns a single page document containing all the elements after the given element"""
        elements = self.elements
        element_ids = [id(el) for el in elements]
        start_idx = element_ids.index(id(element)) + 1
        return self.__class__.from_elements(elements[start_idx:])

    def before_element(self, element: Element) -> Document:
        """Returns a single page document containing all the elements before the given element"""
        elements = self.elements
        element_ids = [id(el) for el in elements]
        end_idx = element_ids.index(id(element))
        return self.__class__.from_elements(elements[:end_idx])

    def print_narrative(self):
        """Prints the narrative text sections of the document."""
        print("\n\n".join([str(el) for el in self.get_narrative()]))

    @classmethod
    def from_elements(cls, elements: List[Element]) -> Document:
        """Generates a new instance of the class from a list of `Element`s"""
        if elements:
            page = Page(number=0)
            page.elements = elements
            pages = [page]
        else:
            pages = []
        return cls.from_pages(pages)

    @classmethod
    def from_pages(cls, pages: List[Page]) -> Document:
        """Generates a new instance of the class from a list of `Page`s"""
        doc = cls()
        doc._pages = pages
        return doc


class Page(ABC):
    """A page consists of an ordered set of elements. The intent of the ordering is to align
    with the order in which a person would read the document."""

    def __init__(self, number: int):
        self.number: int = number
        self.elements: List[Element] = []

    def __str__(self):
        return "\n\n".join([str(element) for element in self.elements])
