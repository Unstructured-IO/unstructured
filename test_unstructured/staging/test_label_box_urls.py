import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from unstructured.documents.elements import Text
from unstructured.staging.label_box import stage_for_label_box


@pytest.fixture()
def hosted_directory(tmp_path):
    directory = tmp_path / "source folder"
    directory.mkdir()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(tmp_path))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        thread.start()
        try:
            yield directory, f"http://127.0.0.1:{server.server_port}/source%20folder"
        finally:
            server.shutdown()
            thread.join()


@pytest.mark.parametrize("trailing_slash", ["", "/"])
@pytest.mark.parametrize(
    ("external_id", "url_id"),
    [
        ("chapter#one", "chapter%23one"),
        ("value%2Fpart", "value%252Fpart"),
        ("value%25part", "value%2525part"),
        ("white space", "white%20space"),
        ("café", "caf%C3%A9"),
        ("bracket[1]", "bracket%5B1%5D"),
    ],
)
def test_custom_identifiers_produce_urls_for_the_files_actually_written(
    hosted_directory, external_id, url_id, trailing_slash
):
    directory, prefix = hosted_directory
    element = Text("The complete source text.")
    config = stage_for_label_box(
        [element], str(directory), prefix + trailing_slash, external_ids=[external_id]
    )[0]

    response = requests.get(config["data"], timeout=5)

    assert response.status_code == 200
    assert response.text == element.text
    assert config["data"] == f"{prefix}/{url_id}.txt"
    assert config["externalId"] == external_id
    assert (directory / f"{external_id}.txt").read_text() == element.text


@pytest.mark.parametrize("external_id", [None, "safe-id_1.2~3"])
def test_unreserved_identifiers_keep_their_existing_urls(hosted_directory, external_id):
    directory, prefix = hosted_directory
    element = Text("Source text")
    ids = None if external_id is None else [external_id]

    config = stage_for_label_box([element], str(directory), prefix, external_ids=ids)[0]

    expected_id = element.id if external_id is None else external_id
    assert config["data"] == f"{prefix}/{expected_id}.txt"
    assert config["externalId"] == expected_id
    assert requests.get(config["data"], timeout=5).text == element.text
