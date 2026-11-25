"""Follow actual HTTP redirects without replaying the initial query parameters."""

import copy
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

import pytest
import requests

from unstructured.safe_http import safe_get


@pytest.fixture
def redirect_server():
    state = {"requests": [], "status": 302, "target": "/final", "hops": 1}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"].append(self.path)
            path = urlsplit(self.path).path
            if path == "/start" or (path == "/middle" and state["hops"] == 2):
                self.send_response(state["status"])
                target = (
                    "/middle?hop=1" if path == "/start" and state["hops"] == 2 else state["target"]
                )
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = b"Fetched document."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("target", ["/final", "/final?source=server&target=1"])
def test_redirect_queries_match_requests_without_replaying_initial_params(
    status, target, redirect_server
):
    base_url, state = redirect_server
    state.update(status=status, target=target)
    params = [("source", "one"), ("source", "two")]
    before = copy.deepcopy(params)

    with requests.get(base_url + "/start?existing=1", params=params, timeout=5) as reference:
        assert reference.text == "Fetched document."
    expected_paths = list(state["requests"])
    state["requests"].clear()

    with safe_get(
        base_url + "/start?existing=1", allow_private=True, params=params, timeout=5
    ) as result:
        assert result.text == "Fetched document."
        assert result.url == base_url + target

    assert state["requests"] == expected_paths
    assert parse_qsl(urlsplit(state["requests"][0]).query) == [
        ("existing", "1"),
        ("source", "one"),
        ("source", "two"),
    ]
    assert state["requests"][1] == target
    assert params == before


def test_initial_params_are_not_reintroduced_on_later_redirect_hops(redirect_server):
    base_url, state = redirect_server
    state.update(hops=2, target="/final?server=1")

    with safe_get(
        base_url + "/start", allow_private=True, params={"initial": "1"}, timeout=5
    ) as result:
        assert result.text == "Fetched document."

    assert state["requests"] == ["/start?initial=1", "/middle?hop=1", "/final?server=1"]


def test_initial_query_params_are_still_sent_without_a_redirect(redirect_server):
    base_url, state = redirect_server

    with safe_get(
        base_url + "/final", allow_private=True, params={"initial": "1"}, timeout=5
    ) as result:
        assert result.text == "Fetched document."

    assert state["requests"] == ["/final?initial=1"]


def test_redirect_without_params_keeps_its_server_supplied_query(redirect_server):
    base_url, state = redirect_server
    state["target"] = "/final?server=1"

    with safe_get(base_url + "/start", allow_private=True, timeout=5) as result:
        assert result.text == "Fetched document."

    assert state["requests"] == ["/start", "/final?server=1"]
