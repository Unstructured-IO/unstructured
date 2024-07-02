"""Utilities that ease unit-testing."""

from __future__ import annotations

import datetime as dt
import difflib
import pathlib
from typing import Any, List, Optional
from unittest.mock import (
    ANY,
    MagicMock,
    Mock,
    PropertyMock,
    call,
    create_autospec,
    mock_open,
    patch,
)

from pytest import CaptureFixture, FixtureRequest, LogCaptureFixture, MonkeyPatch  # noqa: PT013

from unstructured.documents.elements import Element
from unstructured.staging.base import elements_from_json, elements_to_json

__all__ = (
    "ANY",
    "CaptureFixture",
    "FixtureRequest",
    "LogCaptureFixture",
    "MagicMock",
    "Mock",
    "MonkeyPatch",
    "call",
    "class_mock",
    "function_mock",
    "initializer_mock",
    "instance_mock",
    "method_mock",
    "property_mock",
)


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


def assign_hash_ids(elements: list[Element]) -> list[Element]:
    """Updates the `id` attribute of each element to a hash."""
    for idx, element in enumerate(elements):
        element.id_to_hash(idx)
    return elements


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


def example_doc_text(file_name: str) -> str:
    """Contents of example-doc `file_name` as text (decoded as utf-8)."""
    with open(example_doc_path(file_name)) as f:
        return f.read()


def parse_optional_datetime(datetime_str: Optional[str]) -> Optional[dt.datetime]:
    """Parse `datetime_str` to a datetime.datetime instance or None if `datetime_str` is None."""
    return dt.datetime.fromisoformat(datetime_str) if datetime_str else None


# ------------------------------------------------------------------------------------------------
# MOCKING FIXTURES
# ------------------------------------------------------------------------------------------------
# These allow full-featured and type-safe mocks to be created simply by adding a unit-test
# fixture.
# ------------------------------------------------------------------------------------------------


def class_mock(
    request: FixtureRequest, q_class_name: str, autospec: bool = True, **kwargs: Any
) -> Mock:
    """Return mock patching class with qualified name `q_class_name`.

    The mock is autospec'ed based on the patched class unless the optional argument `autospec` is
    set to False. Any other keyword arguments are passed through to Mock(). Patch is reversed after
    calling test returns.
    """
    _patch = patch(q_class_name, autospec=autospec, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def cls_attr_mock(
    request: FixtureRequest,
    cls: type,
    attr_name: str,
    name: str | None = None,
    **kwargs: Any,
):
    """Return a mock for attribute `attr_name` on `cls`.

    Patch is reversed after pytest uses it.
    """
    name = request.fixturename if name is None else name
    _patch = patch.object(cls, attr_name, name=name, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def function_mock(
    request: FixtureRequest, q_function_name: str, autospec: bool = True, **kwargs: Any
) -> Mock:
    """Return mock patching function with qualified name `q_function_name`.

    Patch is reversed after calling test returns.
    """
    _patch = patch(q_function_name, autospec=autospec, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def initializer_mock(request: FixtureRequest, cls: type, autospec: bool = True, **kwargs: Any):
    """Return mock for __init__() method on `cls`.

    The patch is reversed after pytest uses it.
    """
    _patch = patch.object(cls, "__init__", autospec=autospec, return_value=None, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def instance_mock(
    request: FixtureRequest,
    cls: type,
    name: str | None = None,
    spec_set: bool = True,
    **kwargs: Any,
):
    """Return a mock for an instance of `cls` that draws its spec from the class.

    The mock does not allow new attributes to be set on the instance. If `name` is missing or
    |None|, the name of the returned |Mock| instance is set to *request.fixturename*. Additional
    keyword arguments are passed through to the Mock() call that creates the mock.
    """
    name = name if name is not None else request.fixturename
    return create_autospec(cls, _name=name, spec_set=spec_set, instance=True, **kwargs)


def loose_mock(request: FixtureRequest, name: str | None = None, **kwargs: Any):
    """Return a "loose" mock, meaning it has no spec to constrain calls on it.

    Additional keyword arguments are passed through to Mock(). If called without a name, it is
    assigned the name of the fixture.
    """
    if name is None:
        name = request.fixturename
    return Mock(name=name, **kwargs)


def method_mock(
    request: FixtureRequest,
    cls: type,
    method_name: str,
    autospec: bool = True,
    **kwargs: Any,
):
    """Return mock for method `method_name` on `cls`.

    The patch is reversed after pytest uses it.
    """
    _patch = patch.object(cls, method_name, autospec=autospec, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def open_mock(request: FixtureRequest, module_name: str, **kwargs: Any):
    """Return a mock for the builtin `open()` method in `module_name`."""
    target = "%s.open" % module_name
    _patch = patch(target, mock_open(), create=True, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def property_mock(request: FixtureRequest, cls: type, prop_name: str, **kwargs: Any) -> Mock:
    """A mock for property `prop_name` on class `cls`.

    Patch is reversed at the end of the test run.
    """
    _patch = patch.object(cls, prop_name, new_callable=PropertyMock, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()


def var_mock(request: FixtureRequest, q_var_name: str, **kwargs: Any):
    """Return a mock patching the variable with qualified name `q_var_name`.

    Patch is reversed after calling test returns.
    """
    _patch = patch(q_var_name, **kwargs)
    request.addfinalizer(_patch.stop)
    return _patch.start()
