from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import ElementMetadata, Image
from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import create_file_from_elements


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
