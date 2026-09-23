from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, cast

import numpy as np
from PIL.Image import Image

from unstructured_inference.constants import ElementType
from unstructured_inference.inference.elements import (
    grow_region_to_match_region,
    intersections,
)
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    LayoutElements,
    clean_layoutelements,
    partition_groups_from_regions,
    separate,
)


class UnstructuredModel(ABC):
    """Wrapper class for the various models used by unstructured."""

    def __init__(self):
        """model should support inference of some sort, either by calling or by some method.
        UnstructuredModel doesn't provide any training interface, it's assumed the model is
        already trained.
        """
        self.model = None

    @abstractmethod
    def predict(self, x: Any) -> Any:
        """Do inference using the wrapped model."""
        if self.model is None:
            raise ModelNotInitializedError(
                "Model has not been initialized. Please call the initialize method with the "
                "appropriate arguments for loading the model.",
            )
        pass  # pragma: no cover

    def __call__(self, x: Any) -> Any:
        """Inference using function call interface."""
        return self.predict(x)

    @abstractmethod
    def initialize(self, *args, **kwargs):
        """Load the model for inference."""
        pass  # pragma: no cover


class UnstructuredObjectDetectionModel(UnstructuredModel):
    """Wrapper class for object detection models used by unstructured."""

    @abstractmethod
    def predict(self, x: Image) -> LayoutElements | list[LayoutElement]:
        """Do inference using the wrapped model."""
        super().predict(x)
        return []

    def __call__(self, x: Image) -> LayoutElements:
        """Inference using function call interface."""
        return super().__call__(x)

    @staticmethod
    def enhance_regions(
        elements: List[LayoutElement],
        iom_to_merge: float = 0.3,
    ) -> List[LayoutElement]:
        """This function traverses all the elements and either deletes nested elements,
        or merges or splits them depending on the iom score for both regions"""
        rects = [el.bbox for el in elements]
        intersections_mtx = intersections(*rects)

        for i, row in enumerate(intersections_mtx):
            first = elements[i]
            if first:
                # We get only the elements which intersected
                indices_to_check = np.where(row)[0]
                # Delete the first element, since it will always intersect with itself
                indices_to_check = indices_to_check[indices_to_check != i]
                if len(indices_to_check) == 0:
                    continue
                if len(indices_to_check) > 1:  # sort by iom
                    iom_to_check = [
                        (j, first.bbox.intersection_over_minimum(elements[j].bbox))
                        for j in indices_to_check
                        if elements[j] is not None
                    ]
                    iom_to_check.sort(
                        key=lambda x: x[1],
                        reverse=True,
                    )  # sort elements by iom, so we first check the greatest
                    indices_to_check = [x[0] for x in iom_to_check if x[0] != i]  # type:ignore
                for j in indices_to_check:
                    if elements[j] is None or elements[i] is None:
                        continue
                    second = elements[j]
                    intersection = first.bbox.intersection(
                        second.bbox,
                    )  # we know it does, but need the region
                    first_inside_second = first.bbox.is_in(second.bbox)
                    second_inside_first = second.bbox.is_in(first.bbox)

                    if first_inside_second and not second_inside_first:
                        elements[i] = None  # type:ignore
                    elif second_inside_first and not first_inside_second:
                        # delete second element
                        elements[j] = None  # type:ignore
                    elif intersection:
                        iom = first.bbox.intersection_over_minimum(second.bbox)
                        if iom < iom_to_merge:  # small
                            separate(first.bbox, second.bbox)
                            # The rectangle could become too small, which is a
                            # good size to delete?
                        else:  # big
                            # merge
                            if first.bbox.area > second.bbox.area:
                                grow_region_to_match_region(first.bbox, second.bbox)
                                elements[j] = None  # type:ignore
                            else:
                                grow_region_to_match_region(second.bbox, first.bbox)
                                elements[i] = None  # type:ignore

        elements = [e for e in elements if e is not None]
        return elements

    @staticmethod
    def clean_type(
        elements: list[LayoutElement],
        type_to_clean=ElementType.TABLE,
    ) -> List[LayoutElement]:
        """After this function, the list of elements will not contain any element inside
        of the type specified"""
        target_elements = [e for e in elements if e.type == type_to_clean]
        other_elements = [e for e in elements if e.type != type_to_clean]
        if len(target_elements) == 0 or len(other_elements) == 0:
            return elements

        # Sort elements from biggest to smallest
        target_elements.sort(key=lambda e: e.bbox.area, reverse=True)
        other_elements.sort(key=lambda e: e.bbox.area, reverse=True)

        # First check if targets contains each other
        for element in target_elements:  # Just handles containment or little overlap
            contains = [
                e
                for e in target_elements
                if e.bbox.is_almost_subregion_of(element.bbox) and e != element
            ]
            for contained in contains:
                target_elements.remove(contained)
        # Then check if remaining elements intersect with targets
        other_elements = filter(
            lambda e: (
                not any(e.bbox.is_almost_subregion_of(target.bbox) for target in target_elements)
            ),
            other_elements,
        )  # type:ignore

        final_elements = list(other_elements)
        final_elements.extend(target_elements)
        # Note(benjamin): could use bisect.insort if < operator is added to LayoutElement
        final_elements.sort(key=lambda e: e.bbox.y1)
        return final_elements

    def deduplicate_detected_elements(
        self,
        elements: LayoutElements,
        min_text_size: int = 15,
    ) -> LayoutElements:
        """Deletes overlapping elements in a list of elements."""

        if len(elements) <= 1:
            return elements

        cleaned_elements = []
        # TODO: Delete nested elements with low or None probability
        # TODO: Keep most confident
        # TODO: Better to grow horizontally than vertically?
        groups = cast(list[LayoutElements], partition_groups_from_regions(elements))
        for group in groups:
            cleaned_elements.append(clean_layoutelements(group))
        return LayoutElements.concatenate(cleaned_elements)


class UnstructuredElementExtractionModel(UnstructuredModel):
    """Wrapper class for object extraction models used by unstructured."""

    @abstractmethod
    def predict(self, x: Image) -> List[LayoutElement]:
        """Do inference using the wrapped model."""
        super().predict(x)
        return []  # pragma: no cover

    def __call__(self, x: Image) -> List[LayoutElement]:
        """Inference using function call interface."""
        return super().__call__(x)


class ModelNotInitializedError(Exception):
    pass
