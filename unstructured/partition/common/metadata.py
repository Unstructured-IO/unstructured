"""Helpers used across multiple partitioners to compute metadata."""

from __future__ import annotations

import datetime as dt
import functools
import os
from typing import Any, Callable, Sequence

from typing_extensions import ParamSpec

from unstructured.documents.elements import Element, ElementMetadata, assign_and_map_hash_ids
from unstructured.file_utils.model import FileType
from unstructured.partition.common.lang import apply_lang_metadata
from unstructured.utils import get_call_args_applying_defaults

_P = ParamSpec("_P")


def get_last_modified_date(filename: str) -> str | None:
    """Modification time of file at path `filename`, if it exists.

    Returns `None` when `filename` is not a path to a file on the local filesystem.

    Otherwise returns date and time in ISO 8601 string format (YYYY-MM-DDTHH:MM:SS) like
    "2024-03-05T17:02:53".
    """
    if not os.path.isfile(filename):
        return None

    modify_date = dt.datetime.fromtimestamp(os.path.getmtime(filename))
    return modify_date.strftime("%Y-%m-%dT%H:%M:%S%z")


HIERARCHY_RULE_SET = {
    "Title": [
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "ListItem",
        "BulletedText",
        "Table",
        "FigureCaption",
        "CheckBox",
        "Table",
    ],
    "Header": [
        "Title",
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "ListItem",
        "BulletedText",
        "Table",
        "FigureCaption",
        "CheckBox",
        "Table",
    ],
}


def set_element_hierarchy(
    elements: Sequence[Element], ruleset: dict[str, list[str]] = HIERARCHY_RULE_SET
) -> list[Element]:
    """Sets `.metadata.parent_id` for each element it applies to.

    `parent_id` assignment is based on the element's category, depth and a ruleset.
    """
    stack: list[Element] = []
    for element in elements:
        if element.metadata.parent_id is not None:
            continue
        parent_id = None
        element_category = getattr(element, "category", None)
        element_category_depth = getattr(element.metadata, "category_depth", 0) or 0

        if not element_category:
            continue

        while stack:
            top_element: Element = stack[-1]
            top_element_category = getattr(top_element, "category")
            top_element_category_depth = (
                getattr(
                    top_element.metadata,
                    "category_depth",
                    0,
                )
                or 0
            )

            if (
                top_element_category == element_category
                and top_element_category_depth < element_category_depth
            ) or (
                top_element_category != element_category
                and element_category in ruleset.get(top_element_category, [])
            ):
                parent_id = top_element.id
                break

            stack.pop()

        element.metadata.parent_id = parent_id
        stack.append(element)

    return list(elements)


# ================================================================================================
# METADATA POST-PARTITIONING PROCESSING DECORATOR
# ================================================================================================


def apply_metadata(
    file_type: FileType | None = None,
) -> Callable[[Callable[_P, list[Element]]], Callable[_P, list[Element]]]:
    """Post-process element-metadata for this document.

    This decorator adds a post-processing step to a partitioner, primarily to apply metadata that
    is common to all partitioners. It assumes the following responsibilities:

      - Hash element-ids. Computes and applies SHA1 hash element.id when `unique_element_ids`
        argument is False.

      - Element Hierarchy. Computes and applies `parent_id` metadata based on `category_depth`
        etc. added by partitioner.

      - Language metadata. Computes and applies `language` metadata based on a language detection
        model.

      - Apply `filetype` (MIME-type) metadata. There are three cases; first one in this order that
        applies is used:

          - `metadata_file_type` argument is present in call, use that.
          - `file_type` decorator argument is populated, use that.
          - `file_type` decorator argument is omitted or None, don't apply `.metadata.filetype`
            (assume the partitioner will do that for itself, like `partition_image()`.

      - Replace `filename` with `metadata_filename` when present.

      - Apply `url` metadata when present.
    """

    def decorator(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
        """The decorator function itself.

        This function is returned by the `apply_metadata()` function and is the actual decorator.
        Think of `apply_metadata()` as a factory function that configures this decorator, in
        particular by setting its `file_type` value.
        """

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> list[Element]:
            elements = func(*args, **kwargs)
            call_args = get_call_args_applying_defaults(func, *args, **kwargs)

            # -- Compute and apply hash-ids if the user does not want UUIDs. Note this changes the
            # -- elements themselves, not the metadata.
            unique_element_ids: bool = call_args.get("unique_element_ids", False)
            if unique_element_ids is False:
                elements = assign_and_map_hash_ids(elements)

            # -- `parent_id` - process category-level etc. to assign parent-id --
            elements = set_element_hierarchy(elements)

            # -- `language` - auto-detect language (e.g. eng, spa) --
            languages = call_args.get("languages")
            detect_language_per_element = call_args.get("detect_language_per_element", False)
            elements = list(
                apply_lang_metadata(
                    elements=elements,
                    languages=languages,
                    detect_language_per_element=detect_language_per_element,
                )
            )

            # == apply filetype, filename, and url metadata =========================
            metadata_kwargs: dict[str, Any] = {}

            # -- `filetype` (MIME-type) metadata --
            metadata_file_type = call_args.get("metadata_file_type") or file_type
            if metadata_file_type is not None:
                metadata_kwargs["filetype"] = metadata_file_type.mime_type

            # -- `filename` metadata - override with metadata_filename when it's present --
            filename = call_args.get("metadata_filename") or call_args.get("filename")
            if filename:
                metadata_kwargs["filename"] = filename

            # -- `url` metadata - record url when present --
            url = call_args.get("url")
            if url:
                metadata_kwargs["url"] = url

            # -- update element.metadata in single pass --
            for element in elements:
                # NOTE(robinson) - Attached files have already run through this logic in their own
                # partitioning function
                if element.metadata.attached_to_filename:
                    continue
                element.metadata.update(ElementMetadata(**metadata_kwargs))

            return elements

        return wrapper

    return decorator
