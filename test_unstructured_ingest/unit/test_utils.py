import json
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.cli.utils import extract_config
from unstructured.ingest.interfaces import BaseConfig


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
