"""Helpers used across multiple partitioners to compute metadata."""

from __future__ import annotations

import copy
import datetime as dt
import functools
import itertools
import os
from typing import Any, Callable, Iterator, Sequence

from typing_extensions import ParamSpec

from unstructured.documents.elements import Element, ElementMetadata
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

    `parent_id` assignment is based on the element's category and depth. The importance of an
    element's category is determined by a rule set. The rule set trumps category_depth. That is,
    category_depth is only relevant when elements are of the same category.
    """
    stack: list[Element] = []
    for element in elements:
        if element.metadata.parent_id is not None:
            continue
        parent_id = None
        element_category = getattr(element, "category", None)
        element_category_depth = getattr(element.metadata, "category_depth", 0) or 0

        # -- skip elements without a category --
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

      - Replace `last_modified` with `metadata_last_modified` when present.

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

            # ------------------------------------------------------------------------------------
            # unique-ify elements
            # ------------------------------------------------------------------------------------
            # Do this first to ensure all following operations behave as expected. It's easy for a
            # partitioner to re-use an element or metadata instance when its values are common to
            # multiple elements. This can lead to very hard-to diagnose bugs downstream when
            # mutating one element unexpectedly also mutates others (because they are the same
            # instance).
            # ------------------------------------------------------------------------------------

            elements = _uniqueify_elements_and_metadata(elements)

            # ------------------------------------------------------------------------------------
            # apply metadata - do this first because it affects the hash computation.
            # ------------------------------------------------------------------------------------

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

            # == apply filetype, filename, last_modified, and url metadata ===================
            metadata_kwargs: dict[str, Any] = {}

            # -- `filetype` (MIME-type) metadata --
            metadata_file_type = call_args.get("metadata_file_type") or file_type
            if metadata_file_type is not None:
                metadata_kwargs["filetype"] = metadata_file_type.mime_type

            # -- `filename` metadata - override with metadata_filename when it's present --
            filename = call_args.get("metadata_filename") or call_args.get("filename")
            if filename:
                metadata_kwargs["filename"] = filename

            # -- `last_modified` metadata - override with metadata_last_modified when present --
            metadata_last_modified = call_args.get("metadata_last_modified")
            if metadata_last_modified:
                metadata_kwargs["last_modified"] = metadata_last_modified

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

            # ------------------------------------------------------------------------------------
            # compute hash ids (when so requestsd)
            # ------------------------------------------------------------------------------------

            # -- Compute and apply hash-ids if the user does not want UUIDs. Note this mutates the
            # -- elements themselves, not their metadata.
            unique_element_ids: bool = call_args.get("unique_element_ids", False)
            if unique_element_ids is False:
                elements = _assign_hash_ids(elements)

            # ------------------------------------------------------------------------------------
            # assign parent-id - do this after hash computation so parent-id is stable.
            # ------------------------------------------------------------------------------------

            # -- `parent_id` - process category-level etc. to assign parent-id --
            elements = set_element_hierarchy(elements)

            return elements

        return wrapper

    return decorator


def _assign_hash_ids(elements: list[Element]) -> list[Element]:
    """Converts `.id` of each element from UUID to hash.

    The hash is based on the `.text` of the element, but also on its page-number and sequence number
    on that page. This provides for deterministic results even when the document is split into one
    or more fragments for parallel processing.
    """
    # -- generate sequence number for each element on a page --
    page_numbers = [e.metadata.page_number for e in elements]
    page_seq_numbers = [
        seq_on_page
        for _, group in itertools.groupby(page_numbers)
        for seq_on_page, _ in enumerate(group)
    ]

    for element, seq_on_page_counter in zip(elements, page_seq_numbers):
        element.id_to_hash(seq_on_page_counter)

    return elements


def _uniqueify_elements_and_metadata(elements: list[Element]) -> list[Element]:
    """Ensure each of `elements` and their metadata are unique instances.

    This prevents hard-to-diagnose bugs downstream when mutating one element unexpectedly also
    mutates others because they are the same instance.
    """

    def iter_unique_elements(elements: list[Element]) -> Iterator[Element]:
        """Substitute deep-copies of any non-unique elements or metadata in `elements`."""
        seen_elements: set[int] = set()
        seen_metadata: set[int] = set()

        for element in elements:
            if id(element) in seen_elements:
                element = copy.deepcopy(element)
            if id(element.metadata) in seen_metadata:
                element.metadata = copy.deepcopy(element.metadata)
            seen_elements.add(id(element))
            seen_metadata.add(id(element.metadata))
            yield element

    return list(iter_unique_elements(elements))
