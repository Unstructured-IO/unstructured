"""Keep service-account credentials local to each real Vertex AI SDK client."""

import json
import os

import pytest

from unstructured.embed.vertexai import VertexAIEmbeddingConfig


@pytest.fixture(scope="module", autouse=True)
def vertex_dependencies():
    pytest.importorskip("langchain_google_vertexai", minversion="3.2.0")
    pytest.importorskip("langchain")
    pytest.importorskip("cryptography")


@pytest.fixture
def credential_environment(tmp_path, monkeypatch):
    # Isolate the legacy fixed credential path as well when running against the old source.
    original_join = os.path.join
    credential_file = tmp_path / "legacy-credentials.json"

    def isolated_join(*parts):
        if parts == ("/tmp", "google-vertex-app-credentials.json"):
            return str(credential_file)
        return original_join(*parts)

    monkeypatch.setattr("unstructured.embed.vertexai.os.path.join", isolated_join)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return credential_file


@pytest.fixture(scope="module")
def signing_key(vertex_dependencies):
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def service_account_config(project, signing_key):
    from cryptography.hazmat.primitives import serialization

    return VertexAIEmbeddingConfig(
        model_name="gemini-embedding-001",
        api_key=json.dumps(
            {
                "type": "service_account",
                "project_id": project,
                "private_key_id": "local-test-key",
                "private_key": signing_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ).decode(),
                "client_email": f"reader@{project}.iam.gserviceaccount.com",
                "token_uri": "http://127.0.0.1:1/not-contacted",
            }
        ),
    )


@pytest.mark.parametrize("project", ["first-test-project", "second-test-project"])
def test_client_receives_its_own_parsed_credentials_and_project(
    project, signing_key, credential_environment
):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from google.oauth2.service_account import Credentials

    client = service_account_config(project, signing_key).get_client()
    try:
        assert isinstance(client.credentials, Credentials)
        assert client.credentials.service_account_email == (
            f"reader@{project}.iam.gserviceaccount.com"
        )
        assert client.credentials.project_id == project
        assert client.project == project
        assert client.model_name == "gemini-embedding-001"
        signature = client.credentials.sign_bytes(b"local credential identity")
        signing_key.public_key().verify(
            signature, b"local credential identity", padding.PKCS1v15(), hashes.SHA256()
        )
    finally:
        client.client.close()


@pytest.mark.parametrize("existing_path", [None, "/existing/application-defaults.json"])
def test_constructing_a_client_does_not_replace_process_credentials_or_write_a_key_file(
    existing_path, signing_key, credential_environment, monkeypatch
):
    if existing_path is not None:
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", existing_path)

    client = service_account_config("isolated-project", signing_key).get_client()
    try:
        assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == existing_path
        assert not credential_environment.exists()
    finally:
        client.client.close()


@pytest.mark.parametrize("order", [("first", "second"), ("second", "first")])
def test_two_configs_keep_distinct_credentials_without_global_registration(
    order, signing_key, credential_environment
):
    clients = [service_account_config(project, signing_key).get_client() for project in order]
    try:
        assert [client.project for client in clients] == list(order)
        assert [client.credentials.service_account_email for client in clients] == [
            f"reader@{project}.iam.gserviceaccount.com" for project in order
        ]
        assert clients[0].credentials is not clients[1].credentials
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ
        assert not credential_environment.exists()
    finally:
        for client in clients:
            client.client.close()


def test_malformed_json_keeps_its_existing_error_without_filesystem_or_environment_changes(
    credential_environment,
):
    config = VertexAIEmbeddingConfig(api_key="{invalid")

    with pytest.raises(json.JSONDecodeError):
        config.get_client()

    assert not credential_environment.exists()
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ
