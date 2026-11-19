import io
import json

import pytest

from unstructured.file_utils import ndjson


@pytest.mark.parametrize("indent", [0, 2, "", "\t"])
def test_dumps_keeps_each_record_on_one_line_when_indent_is_supplied(indent):
    records = [{"nested": {"values": [1, 2]}, "text": "first\nsecond"}, {"value": 3}]

    serialized = ndjson.dumps(records, indent=indent)

    assert len(serialized.splitlines()) == len(records)
    assert [json.loads(line) for line in serialized.splitlines()] == records
    assert ndjson.loads(serialized) == records
    output = io.StringIO()
    ndjson.dump(records, output, indent=indent)
    assert output.getvalue() == serialized


def test_dumps_preserves_other_json_encoder_options():
    records = [{"z": "café", "a": [1, 2]}]

    serialized = ndjson.dumps(
        records, indent=2, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )

    assert serialized == '{"a":[1,2],"z":"café"}'


def test_dumps_preserves_empty_input():
    assert ndjson.dumps([], indent=2) == ""
