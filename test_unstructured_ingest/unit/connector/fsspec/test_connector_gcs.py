from unittest.mock import MagicMock

import pytest

from unstructured.ingest.connector.fsspec.gcs import GcsAccessConfig


@pytest.mark.parametrize(
    ("given_access_token", "then_access_token"),
    [
        (None, None),
        ("/tmp/gcs.key", "/tmp/gcs.key"),
        ("google_default", "google_default"),
        ("cache", "cache"),
        ("anon", "anon"),
        ("browser", "browser"),
        ("cloud", "cloud"),
        ("{'some_key': 'some_value'}", {"some_key": "some_value"}),
    ],
)
def test_validate_access_token(mocker, given_access_token, then_access_token):
    mocked_isfile: MagicMock = mocker.patch("pathlib.Path.is_file")
    mocked_isfile.return_value = True

    when_token = GcsAccessConfig(token=given_access_token).token
    assert when_token == then_access_token


def test_fail_validate_access_token(mocker):
    mocked_isfile: MagicMock = mocker.patch("pathlib.Path.is_file")
    mocked_isfile.return_value = False

    given_access_token = "/tmp/gcs.key"
    with pytest.raises(ValueError):
        GcsAccessConfig(token=given_access_token)
