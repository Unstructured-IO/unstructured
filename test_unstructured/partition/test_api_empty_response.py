import json
from io import BytesIO

import pytest
import requests

from unstructured.documents.elements import NarrativeText
from unstructured.partition.api import partition_multiple_via_api


@pytest.mark.parametrize("use_streams", [False, True])
@pytest.mark.parametrize(
    ("response_documents", "expected_texts"),
    [
        ([], [[]]),
        ([[]], [[]]),
        ([[], []], [[], []]),
        ([NarrativeText("kept").to_dict()], [["kept"]]),
        ([[], [NarrativeText("kept").to_dict()]], [[], ["kept"]]),
    ],
)
def test_batch_partition_preserves_empty_documents(
    tmp_path, mocker, use_streams, response_documents, expected_texts
):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(response_documents).encode()
    post = mocker.patch("unstructured.partition.api.requests.post", return_value=response)
    filenames = [str(tmp_path / f"document-{i}.txt") for i in range(len(expected_texts))]

    if use_streams:
        streams = [BytesIO(b"") for _ in filenames]
        documents = partition_multiple_via_api(files=streams, metadata_filenames=filenames)
        assert all(not stream.closed for stream in streams)
    else:
        for filename in filenames:
            with open(filename, "wb"):
                pass
        documents = partition_multiple_via_api(filenames=filenames)

    assert [[element.text for element in document] for document in documents] == expected_texts
    post.assert_called_once()
