"""Utilities that ease unit-testing."""

import datetime as dt
import difflib
import pathlib
from typing import List, Optional

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

    assert round_tripped_json == original_json, _diff(
        "JSON differs:", round_tripped_json, original_json
    )


def _diff(heading: str, actual: str, expected: str):
    """Diff of actual compared to expected.

    "+" indicates unexpected lines actual, "-" indicates lines missing from actual.
    """
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    heading = "diff: '+': unexpected lines in actual, '-': lines missing from actual\n"
    return heading + "".join(difflib.Differ().compare(actual_lines, expected_lines))


def example_doc_path(file_name: str) -> str:
    """Resolve the absolute-path to `file_name` in the example-docs directory."""
    example_docs_dir = pathlib.Path(__file__).parent.parent / "example-docs"
    file_path = example_docs_dir / file_name
    return str(file_path.resolve())


def parse_optional_datetime(datetime_str: Optional[str]) -> Optional[dt.datetime]:
    """Parse `datetime_str` to a datetime.datetime instance or None if `datetime_str` is None."""
    return dt.datetime.fromisoformat(datetime_str) if datetime_str else None
