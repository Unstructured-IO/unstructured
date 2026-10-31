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
        assert not reader.closed
        assert json.loads(result[0].text) == {"message": "from a pipe"}


@pytest.mark.parametrize("partitioner", [partition_json, partition_ndjson])
def test_seekable_input_is_still_rewound(partitioner):
    stream = io.BytesIO(b'{"message": "seekable"}')
    result = partitioner(file=stream, encoding="utf-8")
    assert json.loads(result[0].text) == {"message": "seekable"}
    assert stream.tell() == 0
    assert not stream.closed
