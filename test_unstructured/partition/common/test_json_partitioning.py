"""Test-suite for `unstructured.partition.common.json_partitioning` module."""

from __future__ import annotations

import json

import pytest

from unstructured.documents.elements import CheckBox
from unstructured.partition.common.json_partitioning import (
    is_element_shaped_dict,
    loads_strict_json,
)
from unstructured.partition.json import partition_json

# ================================================================================================
# Describe `is_element_shaped_dict()`
# ================================================================================================


def it_affirms_a_recognized_text_type_with_a_str_text_field():
    assert is_element_shaped_dict({"type": "Title", "text": "x"}) is True


def it_affirms_a_CheckBox_with_a_bool_checked_field():
    assert is_element_shaped_dict({"type": "CheckBox", "checked": True}) is True


def but_it_rejects_a_CheckBox_with_no_checked_field():
    assert is_element_shaped_dict({"type": "CheckBox"}) is False


def and_it_rejects_a_CheckBox_with_a_non_bool_checked_field():
    assert is_element_shaped_dict({"type": "CheckBox", "checked": "yes"}) is False


def it_affirms_a_TableChunk_with_a_str_text_field():
    assert is_element_shaped_dict({"type": "TableChunk", "text": "x"}) is True


def but_it_rejects_a_TableChunk_with_no_text_field():
    assert is_element_shaped_dict({"type": "TableChunk"}) is False


def and_it_rejects_a_TableChunk_with_a_non_str_text_field():
    assert is_element_shaped_dict({"type": "TableChunk", "text": 42}) is False


def it_affirms_an_element_shaped_dict_with_an_explicit_None_metadata():
    assert is_element_shaped_dict({"type": "Title", "text": "x", "metadata": None}) is True


def but_it_rejects_a_dict_with_a_non_dict_metadata():
    assert is_element_shaped_dict({"type": "Title", "text": "x", "metadata": "weird"}) is False


def it_rejects_a_dict_with_an_unrecognized_type():
    # -- a recognizable "text" field is not enough; the type vocabulary is closed --
    assert is_element_shaped_dict({"type": "Widget", "text": "x"}) is False


def it_rejects_a_dict_with_a_non_str_type():
    assert is_element_shaped_dict({"type": 42, "text": "x"}) is False


def and_it_rejects_a_dict_with_an_unhashable_type_without_crashing():
    assert is_element_shaped_dict({"type": ["Title"], "text": "x"}) is False


def it_rejects_a_non_dict_value():
    assert is_element_shaped_dict(["not", "a", "dict"]) is False


# ================================================================================================
# CheckBox round-trip
# ================================================================================================


def it_rehydrates_a_CheckBox_through_partition_json():
    elements = partition_json(text='[{"type": "CheckBox", "checked": true}]')

    assert len(elements) == 1
    assert isinstance(elements[0], CheckBox)
    assert elements[0].checked is True


# ================================================================================================
# Describe `loads_strict_json()`
# ================================================================================================


def it_parses_valid_json_like_json_loads():
    assert loads_strict_json('{"a": 1, "b": [2, 3.5, "x"]}') == {"a": 1, "b": [2, 3.5, "x"]}


@pytest.mark.parametrize("payload", ["NaN", "Infinity", "-Infinity", '{"x": NaN}', "[Infinity]"])
def it_rejects_non_standard_json_constants(payload: str):
    # -- json.loads accepts these by default; loads_strict_json must reject them as malformed --
    with pytest.raises(json.JSONDecodeError):
        loads_strict_json(payload)
