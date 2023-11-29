import json
from dataclasses import Field, dataclass, fields

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.enhanced_dataclass.dataclasses import EnhancedField


@dataclass
class AuthData(EnhancedDataClassJsonMixin):
    username: str
    password: str = enhanced_field(sensitive=True)


def test_enhanced_field():
    fs = fields(AuthData)
    for f in fs:
        if f.name == "username":
            assert isinstance(f, Field)
            assert hasattr(f, "sensitive") is False
        else:
            assert isinstance(f, EnhancedField)
            assert f.sensitive is True


def test_to_json():
    auth = AuthData(username="my name", password="top secret")
    j = auth.to_json(redact_sensitive=True, redacted_text="THIS IS REDACTED")
    expected = json.dumps({"username": "my name", "password": "THIS IS REDACTED"})
    assert j == expected


def test_to_dict():
    auth = AuthData(username="my name", password="top secret")
    d = auth.to_dict(redact_sensitive=True)
    expected = {"username": "my name", "password": "***REDACTED***"}
    assert d == expected
