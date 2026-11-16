import base64

import pytest

from unstructured.documents.elements import Image
from unstructured.partition.html import partition_html

PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPkEpFjYGBgYmBgYGBg"
    "AAAC5gBAXKUgWwAAAABJRU5ErkJggg=="
)


@pytest.mark.parametrize("attribute", ["src", "data-src"])
@pytest.mark.parametrize(
    "source",
    [
        f"data:image/png;base64,{PNG_BASE64}",
        f"data:image/png;name=logo;base64,{PNG_BASE64}",
        f"data:image/png;charset=utf-8;name=logo;base64,{PNG_BASE64}",
        f"DATA:IMAGE/PNG;BASE64,{PNG_BASE64}",
        "data:image/png;base64," + PNG_BASE64.replace("iVB", "%69%56%42").replace("=", "%3D"),
        "data:image/png;base64," + PNG_BASE64[:40] + "\n" + PNG_BASE64[40:],
        f"data:image/png;base64,{PNG_BASE64}#preview",
    ],
    ids=["plain", "parameter", "multiple-parameters", "case", "escaped", "wrapped", "fragment"],
)
def test_data_image_urls_preserve_the_complete_decodable_payload(attribute, source):
    elements = partition_html(
        text=f'<html><body><img {attribute}="{source}" alt="logo"></body></html>',
        languages=[""],
        extract_image_block_to_payload=True,
        extract_image_block_types=["Image"],
    )

    assert len(elements) == 1
    element = elements[0]
    assert isinstance(element, Image)
    assert element.text == "logo"
    assert element.metadata.image_mime_type == "image/png"
    assert element.metadata.image_url is None
    assert base64.b64decode(element.metadata.image_base64) == base64.b64decode(PNG_BASE64)
    assert element.metadata.image_base64.replace("\n", "") == PNG_BASE64


@pytest.mark.parametrize(
    "source",
    [
        "https://example.com/logo.png",
        "data:image/svg+xml,%3Csvg%3E%3C/svg%3E",
        "data:text/plain;base64,dGV4dA==",
        "data:image/png;base64=parameter,not-base64-data",
    ],
)
def test_other_image_sources_keep_their_url(source):
    elements = partition_html(
        text=f'<html><body><img src="{source}" alt="logo"></body></html>',
        languages=[""],
        extract_image_block_to_payload=True,
        extract_image_block_types=["Image"],
    )

    assert len(elements) == 1
    assert elements[0].metadata.image_url == source
    assert elements[0].metadata.image_base64 is None
    assert elements[0].metadata.image_mime_type is None


def test_data_image_payloads_still_require_explicit_extraction():
    elements = partition_html(
        text=f'<html><body><img src="data:image/png;base64,{PNG_BASE64}" alt="logo"></body></html>',
        languages=[""],
    )

    assert len(elements) == 1
    assert elements[0].metadata.image_base64 is None
    assert elements[0].metadata.image_mime_type is None
