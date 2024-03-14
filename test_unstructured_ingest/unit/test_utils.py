import json
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
import pytest

from unstructured.ingest.cli.utils import extract_config
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.utils.string_and_date_utils import json_to_dict, ensure_isoformat_datetime


@dataclass
class A(BaseConfig):
    a: str


@dataclass
class B(BaseConfig):
    a: A
    b: int


flat_data = {"a": "test", "b": 4, "c": True}


def test_extract_config_concrete():
    @dataclass
    class C(BaseConfig):
        b: B
        c: bool

    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": {"a": {"a": "test"}, "b": 4}, "c": True}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_optional():
    @dataclass
    class C(BaseConfig):
        c: bool
        b: t.Optional[B] = None

    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": {"a": {"a": "test"}, "b": 4}, "c": True}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_union():
    @dataclass
    class C(BaseConfig):
        c: bool
        b: t.Optional[t.Union[B, int]] = None

    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": 4, "c": True}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_list():
    @dataclass
    class C(BaseConfig):
        c: t.List[int]
        b: B

    flat_data = {"a": "test", "b": 4, "c": [1, 2, 3]}
    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": {"a": {"a": "test"}, "b": 4}, "c": [1, 2, 3]}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_optional_list():
    @dataclass
    class C(BaseConfig):
        b: B
        c: t.Optional[t.List[int]] = None

    flat_data = {"a": "test", "b": 4, "c": [1, 2, 3]}
    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": {"a": {"a": "test"}, "b": 4}, "c": [1, 2, 3]}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_dataclass_list():
    @dataclass
    class C(BaseConfig):
        c: bool
        b: t.List[B] = field(default_factory=list)

    flat_data = {"a": "test", "c": True}
    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"b": [], "c": True}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_extract_config_dict():
    @dataclass
    class C(BaseConfig):
        c: bool
        b: t.Dict[str, B] = field(default_factory=dict)

    flat_data = {"c": True}
    c = extract_config(flat_data=flat_data, config=C)
    expected_result = {"c": True, "b": {}}
    assert c.to_json(sort_keys=True) == json.dumps(expected_result, sort_keys=True)


def test_json_to_dict_valid_json():
    json_string = '{"key": "value"}'
    expected_result = {"key": "value"}
    assert json_to_dict(json_string) == expected_result
    assert isinstance(json_to_dict(json_string), dict)


def test_json_to_dict_malformed_json():
    json_string = '{"key": "value"'
    expected_result = '{"key": "value"'
    assert json_to_dict(json_string) == expected_result
    assert isinstance(json_to_dict(json_string), str)


def test_json_to_dict_single_quotes():
    json_string = "{'key': 'value'}"
    expected_result = {"key": "value"}
    assert json_to_dict(json_string) == expected_result
    assert isinstance(json_to_dict(json_string), dict)


def test_json_to_dict_path():
    json_string = "/path/to/file.json"
    expected_result = "/path/to/file.json"
    assert json_to_dict(json_string) == expected_result
    assert isinstance(json_to_dict(json_string), str)

def test_ensure_isoformat_datetime_for_datetime():
    dt = ensure_isoformat_datetime(datetime(2021, 1, 1, 12, 0, 0))
    assert dt == "2021-01-01T12:00:00"

def test_ensure_isoformat_datetime_for_string():
    dt = ensure_isoformat_datetime("2021-01-01T12:00:00")
    assert dt == "2021-01-01T12:00:00"

def test_ensure_isoformat_datetime_fails_on_string():
    with pytest.raises(ValueError):
        dt = ensure_isoformat_datetime("bad timestamp")

def test_ensure_isoformat_datetime_fails_on_int():
    with pytest.raises(TypeError):
        dt = ensure_isoformat_datetime(1111)