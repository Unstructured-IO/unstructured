"""Utilities that ease unit-testing."""

import pathlib
from typing import List

from unstructured.documents.elements import Element
from unstructured.staging.base import elements_from_json, elements_to_json


def assert_round_trips_through_JSON(elements: List[Element]) -> None:
    """Raises AssertionError if `elements -> JSON -> List[Element] -> JSON` are not equal.

    The procedure is:

        1. Serialize `elements` to (original) JSON.
        2. Deserialize that JSON to `List[Element]`.
        3. Serialize that `List[Element]` to JSON.
        3. Compare the original and round-tripped JSON, raise if they are different.

    """
    original_json = elements_to_json(elements)
    assert original_json is not None

    round_tripped_elements = elements_from_json(text=original_json)

    round_tripped_json = elements_to_json(round_tripped_elements)
    assert round_tripped_json is not None

    assert (
        round_tripped_json == original_json
    ), f"JSON differs, expected\n{original_json},\ngot\n{round_tripped_json}\n"


def example_doc_path(file_name: str) -> str:
    """Resolve the absolute-path to `file_name` in the example-docs directory."""
    example_docs_dir = pathlib.Path(__file__).parent.parent / "example-docs"
    file_path = example_docs_dir / file_name
    return str(file_path.resolve())
