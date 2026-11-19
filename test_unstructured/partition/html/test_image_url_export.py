from copy import deepcopy
from urllib.parse import urljoin

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import ElementMetadata, Image
from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import create_file_from_elements, elements_from_dicts


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize(
    ("image_url", "image_base64", "exclude_binary", "expected_src"),
    [
        ("https://example.com/figure.png", None, False, "https://example.com/figure.png"),
        ("https://example.com/figure.png", None, True, "https://example.com/figure.png"),
        ("images/figure.png?a=1&b=2", None, False, "images/figure.png?a=1&b=2"),
        (
            'https://example.com/figure.png?caption="A&B"',
            None,
            False,
            'https://example.com/figure.png?caption="A&B"',
        ),
        ("https://example.com/figure.png", "YWJj", False, "data:image/png;base64,YWJj"),
        ("https://example.com/figure.png", "YWJj", True, "https://example.com/figure.png"),
        (None, "YWJj", False, "data:image/png;base64,YWJj"),
        (None, "YWJj", True, None),
        (None, None, False, None),
        ("", None, False, None),
        ("javascript:alert(1)", None, False, None),
        ("vbscript:msgbox(1)", None, False, None),
        ("data:text/html,<script>alert(1)</script>", None, False, None),
    ],
)
def test_image_sources_survive_html_export(
    exporter, image_url, image_base64, exclude_binary, expected_src, tmp_path
):
    metadata = ElementMetadata(image_url=image_url, image_base64=image_base64, page_number=3)
    image = Image(text='A "quoted" <caption> & detail', element_id="image-1", metadata=metadata)
    before = deepcopy(metadata.to_dict())
    if exporter == "elements_to_html":
        result = elements_to_html([image], exclude_binary_image_data=exclude_binary)
    else:
        output = tmp_path / "images.html"
        result = create_file_from_elements(
            iter([image]),
            output_format="html",
            filename=str(output),
            exclude_binary_image_data=exclude_binary,
        )
        assert output.read_text(encoding="utf-8") == result

    soup = BeautifulSoup(result, "html.parser")
    assert len(soup.find_all("img")) == 1
    assert soup.img.get("src") == expected_src
    assert soup.img["alt"] == image.text
    assert set(soup.img.attrs) <= {"src", "alt", "class", "id"}
    assert metadata.to_dict() == before


def test_explicit_image_html_keeps_precedence_over_metadata_sources():
    image = Image(
        text="caption",
        metadata=ElementMetadata(
            image_url="https://example.com/metadata.png",
            image_base64="YWJj",
            text_as_html='<img src="https://example.com/original.png" alt="original">',
        ),
    )

    result = elements_to_html([image], no_group_by_page=True)

    tag = BeautifulSoup(result, "html.parser").img
    assert tag["src"] == "https://example.com/original.png"
    assert tag["alt"] == "original"


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize("deserialize", [False, True])
@pytest.mark.parametrize("exclude_binary", [False, True])
@pytest.mark.parametrize(
    "image_url",
    [
        "data:image/png;base64,YWJj",
        "DATA:image/jpeg;base64,YWJj",
        " \tDa\r\nta:image/webp;base64,YWJj",
        "data:image/gif,%47%49%46%38%39%61",
    ],
)
def test_binary_exclusion_covers_data_urls_in_image_metadata(
    exporter, deserialize, exclude_binary, image_url, tmp_path
):
    serialized = {
        "type": "Image",
        "element_id": "image-data-url",
        "text": "image caption",
        "metadata": {"image_url": image_url, "page_number": 1},
    }
    serialized_before = deepcopy(serialized)
    image = (
        elements_from_dicts([serialized])[0]
        if deserialize
        else Image(
            serialized["text"],
            element_id=serialized["element_id"],
            metadata=ElementMetadata(**serialized["metadata"]),
        )
    )
    before = deepcopy(image.to_dict())

    if exporter == "elements_to_html":
        result = elements_to_html([image], exclude_binary_image_data=exclude_binary)
    else:
        output = tmp_path / "data-image.html"
        result = create_file_from_elements(
            iter([image]),
            output_format="html",
            filename=str(output),
            exclude_binary_image_data=exclude_binary,
        )
        assert output.read_text(encoding="utf-8") == result

    tag = BeautifulSoup(result, "html.parser").img
    assert tag["alt"] == image.text
    assert image.to_dict() == before
    assert serialized == serialized_before
    if exclude_binary:
        assert tag.get("src") is None
    else:
        assert tag.get("src") is not None
        assert "image/" in tag["src"].lower()


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
def test_relative_image_references_remain_literal_at_different_export_locations(exporter, tmp_path):
    image_urls = ["images/chart.png", "images/chart.png", "../assets/chart.png", "data/chart.png"]
    metadata = [
        ElementMetadata(image_url=image_urls[0], url="https://example.com/reports/index.html"),
        ElementMetadata(image_url=image_urls[1], url="https://other.example/documents/index.html"),
        ElementMetadata(
            image_url=image_urls[2], filename="index.html", file_directory=str(tmp_path / "source")
        ),
        ElementMetadata(image_url=image_urls[3]),
    ]
    images = [
        Image("caption", element_id=f"image-{i}", metadata=value)
        for i, value in enumerate(metadata)
    ]
    before = [deepcopy(image.to_dict()) for image in images]
    resolved_sources = []

    for directory in ("first", "second"):
        output = tmp_path / directory / "export" / "images.html"
        output.parent.mkdir(parents=True)
        if exporter == "elements_to_html":
            result = elements_to_html(images, exclude_binary_image_data=True, no_group_by_page=True)
            output.write_text(result, encoding="utf-8")
        else:
            result = create_file_from_elements(
                iter(images),
                output_format="html",
                filename=str(output),
                exclude_binary_image_data=True,
            )
        assert output.read_text(encoding="utf-8") == result
        soup = BeautifulSoup(result, "html.parser")
        assert [image["src"] for image in soup.find_all("img")] == image_urls
        assert soup.find("base") is None
        resolved = [urljoin(output.as_uri(), value) for value in image_urls]
        assert resolved[0] == (output.parent / "images/chart.png").as_uri()
        assert resolved[0] != urljoin(metadata[0].url, image_urls[0])
        resolved_sources.append(resolved)

    assert all(first != second for first, second in zip(*resolved_sources))
    assert [image.to_dict() for image in images] == before
