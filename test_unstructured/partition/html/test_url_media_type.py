"""Exercise HTML media-type admission through an actual HTTP response."""

from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
import requests

from unstructured.file_utils.filetype import detect_filetype
from unstructured.file_utils.model import FileType
from unstructured.partition.auto import partition
from unstructured.partition.html import partition_html

XHTML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    "<h1>Quarterly report</h1>"
    "<p>Revenue increased during the quarter.</p>"
    "<table><tr><td>Revenue</td><td>120</td></tr></table>"
    "</body></html>"
)
HTML_MEDIA_TYPES = (
    "text/html",
    "text/html; charset=utf-8",
    "Text/HTML; charset=utf-8",
    "TEXT/HTML ; charset=utf-8",
    "application/xhtml+xml",
    "application/xhtml+xml; charset=utf-8",
    'Application/XHTML+XML; charset="utf-8"',
)
NON_HTML_MEDIA_TYPES = (
    "text/htmlish",
    "text/html+xml",
    "application/xhtml+xml-extra",
    "text/plain",
    "",
)
RESPONSE_MEDIA_TYPES = {value: value for value in (*HTML_MEDIA_TYPES, *NON_HTML_MEDIA_TYPES)}


@pytest.fixture
def html_server(monkeypatch) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
            requested_type = params.get("type", [None])[0]
            if requested_type is not None and requested_type not in RESPONSE_MEDIA_TYPES:
                self.send_error(400)
                return
            status = int(params.get("status", ["200"])[0])
            self.send_response(status)
            if requested_type is not None:
                self.send_header("Content-Type", RESPONSE_MEDIA_TYPES[requested_type])
            payload = XHTML.encode("utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    # Explicitly permit only the test's local server through the existing application setting.
    monkeypatch.setenv("UNSTRUCTURED_ALLOW_PRIVATE_URL", "true")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/document"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("media_type", HTML_MEDIA_TYPES)
def test_html_url_accepts_registered_html_media_types(html_server, media_type):
    url = f"{html_server}?{urlencode({'type': media_type})}"

    elements = partition_html(url=url, languages=["eng"])
    expected = partition_html(text=XHTML, languages=["eng"])

    assert [(element.category, element.text) for element in elements] == [
        (element.category, element.text) for element in expected
    ]
    assert len(elements) == 3
    assert elements[-1].metadata.text_as_html == expected[-1].metadata.text_as_html
    assert all(element.metadata.url == url for element in elements)


@pytest.mark.parametrize("media_type", NON_HTML_MEDIA_TYPES)
def test_html_url_rejects_non_html_media_types(html_server, media_type):
    url = f"{html_server}?{urlencode({'type': media_type})}"

    with pytest.raises(ValueError, match="Expected content type"):
        partition_html(url=url, languages=["eng"])


def test_html_url_still_rejects_a_missing_media_type(html_server):
    with pytest.raises(ValueError, match="Expected content type"):
        partition_html(url=html_server, languages=["eng"])


def test_html_url_still_rejects_failed_xhtml_responses(html_server):
    url = f"{html_server}?{urlencode({'type': 'application/xhtml+xml', 'status': 503})}"
    with pytest.raises(ValueError, match="503"):
        partition_html(url=url, languages=["eng"])


@pytest.mark.parametrize("line_break", ["\r\n", "\r", "\n"])
def test_html_server_rejects_response_header_injection(html_server, line_break):
    media_type = f"text/html{line_break}X-Injected: yes"
    url = f"{html_server}?{urlencode({'type': media_type})}"

    response = requests.get(url, timeout=5)

    assert response.status_code == 400
    assert "X-Injected" not in response.headers


@pytest.mark.parametrize("extension", [".xhtml", ".xht"])
def test_auto_partition_routes_xhtml_files_to_html(tmp_path, extension):
    path = tmp_path / f"document{extension}"
    path.write_text(XHTML, encoding="utf-8")

    assert detect_filetype(file_path=str(path)) is FileType.HTML
    elements = partition(filename=str(path), languages=["eng"])
    assert [element.category for element in elements] == ["Title", "NarrativeText", "Table"]
    assert elements[-1].metadata.text_as_html is not None


@pytest.mark.parametrize(
    "kwargs",
    [{"content_type": "application/xhtml+xml"}, {"metadata_filename": "document.xhtml"}],
)
def test_auto_partition_routes_xhtml_streams_to_html(kwargs):
    elements = partition(file=BytesIO(XHTML.encode("utf-8")), languages=["eng"], **kwargs)

    assert [element.category for element in elements] == ["Title", "NarrativeText", "Table"]
    assert elements[-1].metadata.text_as_html is not None


def test_auto_partition_routes_xhtml_url_to_html(html_server):
    url = f"{html_server}?{urlencode({'type': 'application/xhtml+xml'})}"

    elements = partition(url=url, languages=["eng"])

    assert [element.category for element in elements] == ["Title", "NarrativeText", "Table"]
    assert elements[-1].metadata.text_as_html is not None


def test_generic_xml_remains_xml(tmp_path):
    payload = b'<?xml version="1.0"?><records><entry>Ordinary XML data</entry></records>'
    path = tmp_path / "document.xml"
    path.write_bytes(payload)

    assert detect_filetype(file_path=str(path)) is FileType.XML
    assert detect_filetype(file=BytesIO(payload), content_type="application/xml") is FileType.XML
