"""Upload supported binary stream kinds through the installed SDK and real HTTP."""

import contextlib
import io
import json
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from unstructured.partition.api import partition_via_api


@pytest.fixture
def api_server():
    uploads = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            uploads.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = json.dumps(
                [
                    {
                        "type": "NarrativeText",
                        "element_id": "uploaded-element",
                        "text": "Parsed upload.",
                        "metadata": {"filetype": "text/plain"},
                    }
                ]
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", uploads
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class NonSeekableBytes(io.RawIOBase):
    def __init__(self, content):
        self._content = io.BytesIO(content)

    def read(self, size=-1):
        return self._content.read(size)

    def readable(self):
        return True


@pytest.mark.parametrize(
    "input_kind",
    [
        "bytesio",
        "spooled-memory",
        "spooled-disk",
        "buffered-random",
        "zip-member",
        "non-seekable",
        "buffered-reader",
        "filename",
    ],
)
@pytest.mark.parametrize("offset", [0, 7])
def test_binary_uploads_are_accepted_without_closing_the_source(
    input_kind, offset, api_server, tmp_path
):
    payload = b"Header\nUploaded document text.\n"
    path = tmp_path / "document.txt"
    path.write_bytes(payload)
    base_url, uploads = api_server
    with contextlib.ExitStack() as stack:
        if input_kind == "bytesio":
            stream = stack.enter_context(io.BytesIO(payload))
        elif input_kind.startswith("spooled"):
            stream = stack.enter_context(tempfile.SpooledTemporaryFile(max_size=1024, mode="w+b"))
            stream.write(payload)
            if input_kind == "spooled-disk":
                stream.rollover()
        elif input_kind == "buffered-random":
            stream = stack.enter_context(tempfile.TemporaryFile(mode="w+b"))
            stream.write(payload)
        elif input_kind == "zip-member":
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                archive.writestr("document.txt", payload)
            archive = stack.enter_context(zipfile.ZipFile(io.BytesIO(data.getvalue())))
            stream = stack.enter_context(archive.open("document.txt"))
        elif input_kind == "non-seekable":
            stream = stack.enter_context(NonSeekableBytes(payload))
        else:
            stream = stack.enter_context(path.open("rb"))

        if stream.seekable():
            stream.seek(offset)
        else:
            stream.read(offset)
        # The existing BufferedReader path leaves rewinding to the installed SDK.
        expected_content = (
            payload[offset:] if input_kind in ("non-seekable", "buffered-reader") else payload
        )
        source = (
            {"filename": str(path)}
            if input_kind == "filename"
            else {"file": stream, "metadata_filename": "document.txt"}
        )

        elements = partition_via_api(
            **source,
            api_url=base_url,
            api_key="local-test-key",
            strategy="fast",
            retries_max_elapsed_time=1,
        )

        assert [element.text for element in elements] == ["Parsed upload."]
        assert elements[0].metadata.filetype == "text/plain"
        assert len(uploads) == 1
        assert expected_content in uploads[0]
        assert b'filename="document.txt"' in uploads[0] or input_kind == "filename"
        assert not stream.closed
        assert stream.readable()
