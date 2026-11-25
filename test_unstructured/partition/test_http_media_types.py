import pytest
import requests

from unstructured.partition.html import partition_html
from unstructured.partition.md import partition_md


@pytest.fixture(params=[partition_html, partition_md], ids=["html", "markdown"])
def partitioner_response(request, mocker):
    partitioner = request.param
    response = requests.Response()
    response.status_code = 200
    response.encoding = "utf-8"
    response._content = b"<h1>Heading</h1>" if partitioner is partition_html else b"# Heading"
    mocker.patch(f"{partitioner.__module__}.safe_get", return_value=response)
    media_type = "text/html" if partitioner is partition_html else "text/markdown"
    return partitioner, response, media_type


@pytest.mark.parametrize("case", ["lower", "upper", "mixed_with_parameters"])
def test_url_partition_accepts_media_type_case_variants(partitioner_response, case):
    partitioner, response, media_type = partitioner_response
    response.headers["Content-Type"] = {
        "lower": media_type,
        "upper": media_type.upper(),
        "mixed_with_parameters": f"{media_type.title()} ; charset=UTF-8",
    }[case]

    elements = partitioner(url="https://example.test/document", languages=[""])

    assert [element.text for element in elements] == ["Heading"]


@pytest.mark.parametrize("suffix", ["-other", "+json"])
def test_url_partition_rejects_media_types_that_only_share_a_prefix(partitioner_response, suffix):
    partitioner, response, media_type = partitioner_response
    response.headers["Content-Type"] = media_type + suffix

    with pytest.raises(ValueError, match="Expected content type"):
        partitioner(url="https://example.test/document", languages=[""])
