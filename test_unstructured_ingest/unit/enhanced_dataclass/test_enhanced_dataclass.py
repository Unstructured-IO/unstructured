import json
from dataclasses import Field, dataclass, fields

import pytest

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.enhanced_dataclass.dataclasses import EnhancedField


@dataclass
class AuthData(EnhancedDataClassJsonMixin):
    username: str
    password: str = enhanced_field(sensitive=True)
    date: int = enhanced_field(overload_name="time")


auth = AuthData(username="my name", password="top secret", date=3)


def test_enhanced_field():
    fs = fields(AuthData)
    for f in fs:
        if f.name == "username":
            assert isinstance(f, Field)
            assert hasattr(f, "sensitive") is False
        else:
            assert isinstance(f, EnhancedField)
            if f.name == "password":
                assert f.sensitive is True
            else:
                assert not f.sensitive


@pytest.mark.parametrize(
    ("apply_name_overload", "expected_dict"),
    [
        (True, {"username": "my name", "password": "THIS IS REDACTED", "time": 3}),
        (False, {"username": "my name", "password": "THIS IS REDACTED", "date": 3}),
    ],
)
def test_to_json(apply_name_overload: bool, expected_dict: dict):
    j = auth.to_json(
        redact_sensitive=True,
        redacted_text="THIS IS REDACTED",
        apply_name_overload=apply_name_overload,
    )
    expected = json.dumps(expected_dict)
    assert j == expected


@pytest.mark.parametrize(
    ("apply_name_overload", "expected_dict"),
    [
        (True, {"username": "my name", "password": "***REDACTED***", "time": 3}),
        (False, {"username": "my name", "password": "***REDACTED***", "date": 3}),
    ],
)
def test_to_dict(apply_name_overload: bool, expected_dict: dict):
    d = auth.to_dict(redact_sensitive=True, apply_name_overload=apply_name_overload)
    assert d == expected_dict
