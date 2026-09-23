from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Union

import numpy as np
from pandas import DataFrame
from scipy.sparse.csgraph import connected_components

from unstructured_inference.config import inference_config
from unstructured_inference.constants import IsExtracted, Source
from unstructured_inference.inference.elements import (
    Rectangle,
    TextRegion,
    TextRegions,
    coords_intersections,
)

EPSILON_AREA = 1e-7


@dataclass
class LayoutElements(TextRegions):
    element_probs: np.ndarray = field(default_factory=lambda: np.array([]))
    element_class_ids: np.ndarray = field(default_factory=lambda: np.array([]))
    element_class_id_map: dict[int, str] = field(default_factory=dict)
    text_as_html: np.ndarray = field(default_factory=lambda: np.array([]))
    table_as_cells: np.ndarray = field(default_factory=lambda: np.array([]))
    table_extraction_method: np.ndarray = field(default_factory=lambda: np.array([]))
    routing: str | None = None
    routing_score: float | None = None
    _optional_array_attributes: list[str] = field(
        init=False,
        default_factory=lambda: [
            "texts",
            "sources",
            "is_extracted_array",
            "element_probs",
            "element_class_ids",
            "text_as_html",
            "table_as_cells",
            "table_extraction_method",
        ],
    )
    _scalar_to_array_mappings: dict[str, str] = field(
        init=False,
        default_factory=lambda: {
            "source": "sources",
            "is_extracted": "is_extracted_array",
        },
    )

    def __post_init__(self):
        super().__post_init__()
        self.element_probs = self.element_probs.astype(float)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LayoutElements):
            return NotImplemented

        mask = ~np.isnan(self.element_probs)
        other_mask = ~np.isnan(other.element_probs)
        return (
            np.array_equal(self.element_coords, other.element_coords)
            and np.array_equal(self.texts, other.texts)
            and np.array_equal(mask, other_mask)
            and np.array_equal(self.element_probs[mask], other.element_probs[mask])
            and (
                [self.element_class_id_map[idx] for idx in self.element_class_ids]
                == [other.element_class_id_map[idx] for idx in other.element_class_ids]
            )
            and np.array_equal(self.sources[mask], other.sources[mask])
            and np.array_equal(self.is_extracted_array[mask], other.is_extracted_array[mask])
            and np.array_equal(self.text_as_html[mask], other.text_as_html[mask])
            and np.array_equal(self.table_as_cells[mask], other.table_as_cells[mask])
            and np.array_equal(
                self.table_extraction_method[mask], other.table_extraction_method[mask]
            )
        )

    def __getitem__(self, indices):
        return self.slice(indices)

    def slice(self, indices) -> LayoutElements:
        """slice and return only selected indices"""
        return LayoutElements(
            element_coords=self.element_coords[indices],
            texts=self.texts[indices],
            is_extracted_array=self.is_extracted_array[indices],
            sources=self.sources[indices],
            element_probs=self.element_probs[indices],
            element_class_ids=self.element_class_ids[indices],
            element_class_id_map=self.element_class_id_map,
            text_as_html=self.text_as_html[indices],
            table_as_cells=self.table_as_cells[indices],
            table_extraction_method=self.table_extraction_method[indices],
        )

    @classmethod
    def concatenate(cls, groups: Iterable[LayoutElements]) -> LayoutElements:
        """concatenate a sequence of LayoutElements in order as one LayoutElements"""
        coords, texts, probs, class_ids, sources, is_extracted_array = [], [], [], [], [], []
        text_as_html, table_as_cells, table_extraction_method = [], [], []
        class_id_reverse_map: dict[str, int] = {}
        for group in groups:
            coords.append(group.element_coords)
            texts.append(group.texts)
            probs.append(group.element_probs)
            sources.append(group.sources)
            is_extracted_array.append(group.is_extracted_array)
            text_as_html.append(group.text_as_html)
            table_as_cells.append(group.table_as_cells)
            table_extraction_method.append(group.table_extraction_method)

            idx = group.element_class_ids.copy()
            if group.element_class_id_map:
                for class_id, class_name in group.element_class_id_map.items():
                    if class_name in class_id_reverse_map:
                        idx[group.element_class_ids == class_id] = class_id_reverse_map[class_name]
                        continue
                    new_id = len(class_id_reverse_map)
                    class_id_reverse_map[class_name] = new_id
                    idx[group.element_class_ids == class_id] = new_id
            class_ids.append(idx)

        return cls(
            element_coords=np.concatenate(coords),
            texts=np.concatenate(texts),
            element_probs=np.concatenate(probs),
            element_class_ids=np.concatenate(class_ids),
            element_class_id_map={v: k for k, v in class_id_reverse_map.items()},
            sources=np.concatenate(sources),
            is_extracted_array=np.concatenate(is_extracted_array),
            text_as_html=np.concatenate(text_as_html),
            table_as_cells=np.concatenate(table_as_cells),
            table_extraction_method=np.concatenate(table_extraction_method),
        )

    def iter_elements(self):
        """iter elements as one LayoutElement per iteration; this returns a generator and has less
        memory impact than the as_list method"""
        for (
            (x1, y1, x2, y2),
            text,
            prob,
            class_id,
            source,
            is_extracted,
            text_as_html,
            table_as_cells,
            table_extraction_method,
        ) in zip(
            self.element_coords,
            self.texts,
            self.element_probs,
            self.element_class_ids,
            self.sources,
            self.is_extracted_array,
            self.text_as_html,
            self.table_as_cells,
            self.table_extraction_method,
        ):
            yield LayoutElement.from_coords(
                x1,
                y1,
                x2,
                y2,
                text=text,
                type=(
                    self.element_class_id_map[class_id]
                    if class_id is not None and self.element_class_id_map
                    else None
                ),
                prob=None if np.isnan(prob) else prob,
                source=source,
                is_extracted=is_extracted,
                text_as_html=text_as_html,
                table_as_cells=table_as_cells,
                table_extraction_method=table_extraction_method,
            )

    @classmethod
    def from_list(cls, elements: list):
        """create LayoutElements from a list of LayoutElement objects; the objects must have the
        same source"""
        len_ele = len(elements)
        coords = np.empty((len_ele, 4), dtype=float)
        # text and probs can be Nones so use lists first then convert into array to avoid them being
        # filled as nan
        (
            texts,
            text_as_html,
            table_as_cells,
            table_extraction_method,
            sources,
            is_extracted_array,
            class_probs,
        ) = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        class_types = np.empty((len_ele,), dtype="object")

        for i, element in enumerate(elements):
            coords[i] = [element.bbox.x1, element.bbox.y1, element.bbox.x2, element.bbox.y2]
            texts.append(element.text)
            sources.append(element.source)
            is_extracted_array.append(element.is_extracted)
            text_as_html.append(element.text_as_html)
            table_as_cells.append(element.table_as_cells)
            table_extraction_method.append(getattr(element, "table_extraction_method", None))
            class_probs.append(element.prob)
            class_types[i] = element.type or "None"

        unique_ids, class_ids = np.unique(class_types, return_inverse=True)
        unique_ids[unique_ids == "None"] = None

        return cls(
            element_coords=coords,
            texts=np.array(texts),
            element_probs=np.array(class_probs),
            element_class_ids=class_ids,
            element_class_id_map=dict(zip(range(len(unique_ids)), unique_ids)),
            sources=np.array(sources),
            is_extracted_array=np.array(is_extracted_array),
            text_as_html=np.array(text_as_html),
            table_as_cells=np.array(table_as_cells),
            table_extraction_method=np.array(table_extraction_method),
        )


@dataclass
class LayoutElement(TextRegion):
    type: Optional[str] = None
    prob: Optional[float] = None
    image_path: Optional[str] = None
    parent: Optional[LayoutElement] = None
    text_as_html: Optional[str] = None
    table_as_cells: Optional[str] = None
    table_extraction_method: Optional[str] = None

    def to_dict(self) -> dict:
        """Converts the class instance to dictionary form."""
        out_dict = {
            "coordinates": None if self.bbox is None else self.bbox.coordinates,
            "text": self.text,
            "type": self.type,
            "prob": self.prob,
            "source": self.source,
            "is_extracted": self.is_extracted,
        }
        return out_dict

    @classmethod
    def from_region(cls, region: TextRegion):
        """Create LayoutElement from superclass."""
        text = region.text if hasattr(region, "text") else None
        type = region.type if hasattr(region, "type") else None
        prob = region.prob if hasattr(region, "prob") else None
        source = region.source if hasattr(region, "source") else None
        is_extracted = region.is_extracted if hasattr(region, "is_extracted") else None
        return cls(
            bbox=region.bbox,
            text=text,
            source=source,
            is_extracted=is_extracted,
            type=type,
            prob=prob,
        )

    @classmethod
    def from_coords(
        cls,
        x1: Union[int, float],
        y1: Union[int, float],
        x2: Union[int, float],
        y2: Union[int, float],
        text: Optional[str] = None,
        source: Optional[Source] = None,
        is_extracted: Optional[IsExtracted] = None,
        type: Optional[str] = None,
        prob: Optional[float] = None,
        text_as_html: Optional[str] = None,
        table_as_cells: Optional[str] = None,
        table_extraction_method: Optional[str] = None,
        **kwargs,
    ) -> LayoutElement:
        """Constructs a LayoutElement from coordinates."""
        bbox = Rectangle(x1, y1, x2, y2)
        return cls(
            text=text,
            is_extracted=is_extracted,
            type=type,
            prob=prob,
            source=source,
            text_as_html=text_as_html,
            table_as_cells=table_as_cells,
            table_extraction_method=table_extraction_method,
            bbox=bbox,
            **kwargs,
        )


def separate(region_a: Rectangle, region_b: Rectangle):
    """Reduce leftmost rectangle to don't overlap with the other"""

    def reduce(keep: Rectangle, reduce: Rectangle):
        # Asume intersection

        # Other is down
        if reduce.y2 > keep.y2 and reduce.x1 < keep.x2:
            # other is down-right
            if reduce.x2 > keep.x2 and reduce.y2 > keep.y2:
                reduce.x1 = keep.x2 * 1.01
                reduce.y1 = keep.y2 * 1.01
                return
            # other is down-left
            if reduce.x1 < keep.x1 and reduce.y1 < keep.y2:
                reduce.y1 = keep.y2
                return
            # other is centered
            reduce.y1 = keep.y2
        else:  # other is up
            # other is up-right
            if reduce.x2 > keep.x2 and reduce.y1 < keep.y1:
                reduce.y2 = keep.y1
                return
            # other is left
            if reduce.x1 < keep.x1 and reduce.y1 < keep.y1:
                reduce.y2 = keep.y1
                return
            # other is centered
            reduce.y2 = keep.y1

    if not region_a.intersects(region_b):
        return
    else:
        if region_a.area > region_b.area:
            reduce(keep=region_a, reduce=region_b)
        else:
            reduce(keep=region_b, reduce=region_a)


def table_cells_to_dataframe(
    cells: List[dict],
    nrows: int = 1,
    ncols: int = 1,
    header=None,
) -> DataFrame:
    """convert table-transformer's cells data into a pandas dataframe"""
    arr = np.empty((nrows, ncols), dtype=object)
    for cell in cells:
        rows = cell["row_nums"]
        cols = cell["column_nums"]
        if rows[0] >= nrows or cols[0] >= ncols:
            new_arr = np.empty((max(rows[0] + 1, nrows), max(cols[0] + 1, ncols)), dtype=object)
            new_arr[:nrows, :ncols] = arr
            arr = new_arr
            nrows, ncols = arr.shape
        arr[rows[0], cols[0]] = cell["cell text"]

    return DataFrame(arr, columns=header)


def partition_groups_from_regions(regions: TextRegions) -> List[TextRegions]:
    """Partitions regions into groups of regions based on proximity. Returns list of lists of
    regions, each list corresponding with a group"""
    if len(regions) == 0:
        return []
    padded_coords = regions.element_coords.copy().astype(float)
    v_pad = (regions.y2 - regions.y1) * inference_config.ELEMENTS_V_PADDING_COEF
    h_pad = (regions.x2 - regions.x1) * inference_config.ELEMENTS_H_PADDING_COEF
    padded_coords[:, 0] -= h_pad
    padded_coords[:, 1] -= v_pad
    padded_coords[:, 2] += h_pad
    padded_coords[:, 3] += v_pad

    intersection_mtx = coords_intersections(padded_coords)

    group_count, group_nums = connected_components(intersection_mtx)
    groups: List[TextRegions] = []
    for group in range(group_count):
        groups.append(regions.slice(np.where(group_nums == group)[0]))

    return groups


def intersection_areas_between_coords(
    coords1: np.ndarray,
    coords2: np.ndarray,
    threshold: float = 0.5,
):
    """compute intersection area and own areas for two groups of bounding boxes"""
    x11, y11, x12, y12 = np.split(coords1, 4, axis=1)
    x21, y21, x22, y22 = np.split(coords2, 4, axis=1)

    xa = np.maximum(x11, np.transpose(x21))
    ya = np.maximum(y11, np.transpose(y21))
    xb = np.minimum(x12, np.transpose(x22))
    yb = np.minimum(y12, np.transpose(y22))

    return np.maximum((xb - xa), 0) * np.maximum((yb - ya), 0)


def clean_layoutelements(elements: LayoutElements, subregion_threshold: float = 0.5):
    """After this function, the list of elements will not contain any element inside
    of the type specified"""
    # Sort elements from biggest to smallest
    if len(elements) < 2:
        return elements

    sorted_by_area = np.argsort(-elements.areas)
    sorted_coords = elements.element_coords[sorted_by_area]

    # First check if targets contains each other
    self_intersection = intersection_areas_between_coords(sorted_coords, sorted_coords)
    areas = elements.areas[sorted_by_area]
    # check from largest to smallest regions to find if it contains any other regions
    is_almost_subregion_of = (
        self_intersection / np.maximum(areas, EPSILON_AREA) > subregion_threshold
    ) & (areas <= areas.T)

    n_candidates = len(elements)
    mask = np.ones_like(areas, dtype=bool)
    current_candidate = 0
    while n_candidates > 1:
        plus_one = current_candidate + 1
        remove = (
            np.where(is_almost_subregion_of[current_candidate, plus_one:])[0]
            + current_candidate
            + 1
        )

        if not remove.sum():
            break

        mask[remove] = 0
        n_candidates -= len(remove) + 1
        remaining_candidates = np.where(mask[plus_one:])[0]

        if not len(remaining_candidates):
            break

        current_candidate = remaining_candidates[0] + plus_one

    final_coords = sorted_coords[mask]
    sorted_by_y1 = np.argsort(final_coords[:, 1])

    final_attrs: dict[str, Any] = {
        "element_class_id_map": elements.element_class_id_map,
    }
    for attr in (
        "element_class_ids",
        "element_probs",
        "texts",
        "sources",
        "is_extracted_array",
        "text_as_html",
        "table_as_cells",
        "table_extraction_method",
    ):
        if (original_attr := getattr(elements, attr)) is None:
            continue
        final_attrs[attr] = original_attr[sorted_by_area][mask][sorted_by_y1]
    final_elements = LayoutElements(element_coords=final_coords[sorted_by_y1], **final_attrs)
    return final_elements


def clean_layoutelements_for_class(
    elements: LayoutElements,
    element_class: int,
    subregion_threshold: float = 0.5,
):
    """After this function, the list of elements will not contain any element inside
    of the type specified"""
    # Sort elements from biggest to smallest
    sorted_by_area = np.argsort(-elements.areas)
    sorted_coords = elements.element_coords[sorted_by_area]

    target_indices = elements.element_class_ids[sorted_by_area] == element_class

    # skip trivial result
    len_target = target_indices.sum()
    if len_target == 0 or len_target == len(elements):
        return elements

    target_coords = sorted_coords[target_indices]
    other_coords = sorted_coords[~target_indices]

    # First check if targets contains each other
    target_self_intersection = intersection_areas_between_coords(target_coords, target_coords)
    target_areas = elements.areas[sorted_by_area][target_indices]
    # check from largest to smallest regions to find if it contains any other regions
    is_almost_subregion_of = (
        target_self_intersection / np.maximum(target_areas, EPSILON_AREA) > subregion_threshold
    ) & (target_areas <= target_areas.T)

    n_candidates = len_target
    mask = np.ones_like(target_areas, dtype=bool)
    current_candidate = 0
    while n_candidates > 1:
        plus_one = current_candidate + 1
        remove = (
            np.where(is_almost_subregion_of[current_candidate, plus_one:])[0]
            + current_candidate
            + 1
        )

        if not remove.sum():
            break

        mask[remove] = 0
        n_candidates -= len(remove) + 1
        remaining_candidates = np.where(mask[plus_one:])[0]

        if not len(remaining_candidates):
            break

        current_candidate = remaining_candidates[0] + plus_one

    target_coords_to_keep = target_coords[mask]

    other_to_target_intersection = intersection_areas_between_coords(
        other_coords,
        target_coords_to_keep,
    )
    # check from largest to smallest regions to find if it contains any other regions
    other_areas = elements.areas[sorted_by_area][~target_indices]
    other_is_almost_subregion_of_target = (
        other_to_target_intersection / np.maximum(other_areas, EPSILON_AREA) > subregion_threshold
    ) & (other_areas.reshape((-1, 1)) <= target_areas[mask].T)

    other_mask = ~other_is_almost_subregion_of_target.sum(axis=1).astype(bool)

    final_coords = np.vstack([target_coords[mask], other_coords[other_mask]])
    final_attrs: dict[str, Any] = {"element_class_id_map": elements.element_class_id_map}
    for attr in (
        "element_class_ids",
        "element_probs",
        "texts",
        "sources",
        "is_extracted_array",
        "text_as_html",
        "table_as_cells",
        "table_extraction_method",
    ):
        if (original_attr := getattr(elements, attr)) is None:
            continue
        sorted_attr = original_attr[sorted_by_area]
        final_attrs[attr] = np.concatenate(
            (sorted_attr[target_indices][mask], sorted_attr[~target_indices][other_mask]),
        )
    final_elements = LayoutElements(element_coords=final_coords, **final_attrs)
    return final_elements
