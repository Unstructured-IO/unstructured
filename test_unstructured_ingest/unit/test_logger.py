import json

import pytest

from unstructured.ingest.logger import (
    default_is_data_sensitive,
    hide_sensitive_fields,
    redact_jsons,
)


@pytest.mark.parametrize(
    ("key", "value", "is_sensitive"),
    [
        ("username", "john_smith", False),
        ("password", "13?H%", True),
        ("token", "123", True),
        ("AWS_CREDENTIAL", "aws_credential", True),
        ("AWS_KEY", None, False),
    ],
)
def test_default_is_sensitive(key, value, is_sensitive):
    assert default_is_data_sensitive(key, value) == is_sensitive


def test_hide_sensitive_fields():
    d = {
        "username": "john_smith",
        "password": "13?H%",
        "inner": {
            "token": "123",
            "AWS_KEY": None,
            "inner_j_string": json.dumps(
                {"account_name": "secret name", "client_id": 123, "timestamp": 123}
            ),
        },
    }
    redacted_d = hide_sensitive_fields(d)
    expected_d = {
        "password": "*******",
        "username": "john_smith",
        "inner": {
            "token": "*******",
            "AWS_KEY": None,
            "inner_j_string": json.dumps(
                {"account_name": "*******", "client_id": "*******", "timestamp": 123}
            ),
        },
    }
    assert redacted_d == expected_d


def test_redact_jsons():
    d1 = {
        "username": "john_smith",
        "password": "13?H%",
        "inner": {
            "token": "123",
            "AWS_KEY": None,
            "inner_j_string": json.dumps(
                {"account_name": "secret name", "client_id": 123, "timestamp": 123}
            ),
        },
    }

    d2 = {"username": "tim67", "update_time": 456}
    d3 = {"account_name": "top secret", "host": "http://localhost:8888"}

    sensitive_string = f"Some topic secret info ({json.dumps(d1)} regarding {d2} and {d3})"
    expected_string = (
        'Some topic secret info ({"username": "john_smith", "password": "*******", '
        '"inner": {"token": "*******", "AWS_KEY": null, "inner_j_string": '
        '"{\\"account_name\\": \\"*******\\", \\"client_id\\": \\"*******\\", '
        '\\"timestamp\\": 123}"}} regarding {"username": "tim67", "update_time": 456} '
        'and {"account_name": "*******", "host": "http://localhost:8888"})'
    )
    redacted_string = redact_jsons(sensitive_string)
    assert redacted_string == expected_string
