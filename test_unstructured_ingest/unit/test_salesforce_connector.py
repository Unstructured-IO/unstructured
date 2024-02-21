from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa

from unstructured.ingest.connector.salesforce import SalesforceAccessConfig


def pkey_to_str(key) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def rsa_private_key() -> str:
    return pkey_to_str(rsa.generate_private_key(0x10001, 512))


def brainpoolp512r1_private_key() -> str:
    return pkey_to_str(ec.generate_private_key(ec.BrainpoolP512R1))


def dsa_private_key() -> str:
    return pkey_to_str(dsa.generate_private_key(1024))


@pytest.mark.parametrize(
    ("private_key", "private_key_type"),
    [
        (rsa_private_key(), str),
        (brainpoolp512r1_private_key(), str),
        (dsa_private_key(), str),
        ("some_path/priv.key", Path),
    ],
)
def test_private_key_type(mocker, private_key, private_key_type):
    mocked_isfile: MagicMock = mocker.patch("pathlib.Path.is_file")
    mocked_isfile.return_value = True

    config = SalesforceAccessConfig(consumer_key="asdf", private_key=private_key)
    actual_pkey_value, actual_pkey_type = config.get_private_key_value_and_type()
    assert actual_pkey_type == private_key_type
    assert actual_pkey_value == private_key


def test_private_key_type_fail(mocker):
    mocked_isfile: MagicMock = mocker.patch("pathlib.Path.is_file")
    mocked_isfile.return_value = False

    given_nonexistent_path = "some_path/priv.key"
    with pytest.raises(expected_exception=ValueError):
        config = SalesforceAccessConfig(consumer_key="asdf", private_key=given_nonexistent_path)
        config.get_private_key_value_and_type()
