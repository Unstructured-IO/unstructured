"""The API helper releases its own HTTP transport on every exit path."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import httpx
import pytest
from unstructured_client import UnstructuredClient

from unstructured.partition import api


@pytest.fixture
def sdk_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[UnstructuredClient]:
    """Use a real SDK transport without sending a network request."""
    sdk = UnstructuredClient()
    transport = sdk.sdk_configuration.client
    monkeypatch.setattr(api, "UnstructuredClient", lambda **kwargs: sdk)
    try:
        yield sdk
    finally:
        # -- close even on the unfixed code path, so a failed regression leaks no resources --
        transport.close()


@pytest.mark.parametrize("outcome", ["success", "request-error", "bad-status", "invalid-json"])
def test_partition_via_api_closes_its_http_client(
    outcome: str, sdk_client: UnstructuredClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A response or request failure releases the transport but leaves the upload open."""
    transport = sdk_client.sdk_configuration.client
    filename = tmp_path / "input.txt"
    filename.write_text("A document to partition.")
    response = SimpleNamespace(
        status_code=500 if outcome == "bad-status" else 200,
        raw_response=httpx.Response(200, text="invalid" if outcome == "invalid-json" else "[]"),
    )

    def partition(**kwargs):
        """Return a local response or raise while the HTTP client is still usable."""
        assert not transport.is_closed
        if outcome == "request-error":
            raise RuntimeError("request failed")
        return response

    monkeypatch.setattr(sdk_client.general, "partition", partition)

    with open(filename, "rb") as stream:
        if outcome == "success":
            assert api.partition_via_api(file=stream, metadata_filename="input.txt") == []
        else:
            error_type = {
                "request-error": RuntimeError,
                "bad-status": ValueError,
                "invalid-json": json.JSONDecodeError,
            }[outcome]
            with pytest.raises(error_type):
                api.partition_via_api(file=stream, metadata_filename="input.txt")

        # -- the caller still owns the upload; only the helper's transport is released --
        assert not stream.closed
        assert transport.is_closed


def test_partition_via_api_closes_its_http_client_when_the_input_cannot_be_opened(
    sdk_client: UnstructuredClient, tmp_path: Path
):
    """A file-open failure also exits the client context."""
    transport = sdk_client.sdk_configuration.client

    with pytest.raises(FileNotFoundError):
        api.partition_via_api(filename=str(tmp_path / "missing.txt"))

    assert transport.is_closed


def test_partition_via_api_closes_its_http_client_when_metadata_filename_is_missing(
    sdk_client: UnstructuredClient, tmp_path: Path
):
    """Argument validation after client creation still closes the transport."""
    transport = sdk_client.sdk_configuration.client
    filename = tmp_path / "input.txt"
    filename.write_text("A document to partition.")

    with open(filename, "rb") as stream:
        with pytest.raises(ValueError, match="metadata_filename must be specified"):
            api.partition_via_api(file=stream)

        assert not stream.closed
        assert transport.is_closed
