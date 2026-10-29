"""Test-suite for `unstructured.file_utils.ndjson` module."""

from unstructured.file_utils import ndjson


def test_loads_keeps_a_string_holding_a_unicode_line_separator():
    assert ndjson.loads('{"note": "one two"}\n{"n": 2}\n') == [
        {"note": "one two"},
        {"n": 2},
    ]
