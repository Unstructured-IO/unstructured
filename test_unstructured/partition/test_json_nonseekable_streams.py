"""JSON partitioners accept readable pipes without seeking or owning them."""

import io
import json
import os

import pytest

from unstructured.partition.json import partition_json
from unstructured.partition.ndjson import partition_ndjson


@pytest.mark.parametrize("partitioner", [partition_json, partition_ndjson])
def test_partition_json_from_a_real_pipe(partitioner):
    reader_fd, writer_fd = os.pipe()
    with os.fdopen(writer_fd, "wb") as writer:
        writer.write(b'{"message": "from a pipe"}')
    with os.fdopen(reader_fd, "rb") as reader:
        assert not reader.seekable()
        result = partitioner(file=reader, encoding="utf-8")
        assert reader.read() == b""
        assert not reader.closed
        assert json.loads(result[0].text) == {"message": "from a pipe"}


@pytest.mark.parametrize("partitioner", [partition_json, partition_ndjson])
def test_seekable_input_is_still_rewound(partitioner):
    stream = io.BytesIO(b'{"message": "seekable"}')
    result = partitioner(file=stream, encoding="utf-8")
    assert json.loads(result[0].text) == {"message": "seekable"}
    assert stream.tell() == 0
    assert not stream.closed


class LegacyStream:
    """Readable, rewindable adapter without the optional seekable query."""

    def __init__(self, stream):
        self.stream = stream

    def read(self, *args):
        return self.stream.read(*args)

    def seek(self, *args):
        return self.stream.seek(*args)


@pytest.mark.parametrize("partitioner", [partition_json, partition_ndjson])
@pytest.mark.parametrize("stream_type", [io.BytesIO, io.StringIO])
def test_stream_without_seekable_is_still_rewound(partitioner, stream_type):
    payload = '{"message": "legacy adapter"}'
    content = payload.encode() if stream_type is io.BytesIO else payload
    with stream_type(content) as stream:
        result = partitioner(file=LegacyStream(stream), encoding="utf-8")
        assert len(result) == 1
        assert json.loads(result[0].text) == {"message": "legacy adapter"}
        assert stream.tell() == 0
        assert not stream.closed
