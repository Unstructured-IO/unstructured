from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from markdown import markdown

from unstructured.documents.elements import ElementMetadata, Image, NarrativeText, Title
from unstructured.staging.base import create_file_from_elements, element_to_md, elements_to_md


def rendered_image(text: str):
    soup = BeautifulSoup(markdown(text), "html.parser")
    images = soup.find_all("img")
    assert len(images) == 1, str(soup)
    return images[0]


@pytest.mark.parametrize(
    "caption",
    [
        "Response [ms",
        "The closing bracket ] in the plot",
        r"C:\plots\[draft]",
        "Literal &amp; and &#169;",
        "<span>literal markup</span>",
        "**bold** and _italic_ markers",
        "First line\n\nsecond line",
        "",
    ],
)
def test_image_captions_render_as_literal_alt_text(caption: str):
    url = "https://example.com/figure.png"
    element = Image(caption, metadata=ElementMetadata(image_url=url))

    image = rendered_image(element_to_md(element))

    assert image["alt"] == caption
    assert image["src"] == url
    assert element.text == caption
    assert element.metadata.image_url == url


@pytest.mark.parametrize(
    ("url", "expected_src"),
    [
        ("https://example.com/figure(.png", "https://example.com/figure%28.png"),
        ("https://example.com/figure).png", "https://example.com/figure%29.png"),
        ("images/figure 1.png", "images/figure%201.png"),
        ("https://example.com/图.png", "https://example.com/%E5%9B%BE.png"),
        ("https://example.com/a%20b.png?x=1#section", "https://example.com/a%20b.png?x=1#section"),
        ("https://example.com/a.png?x=&copy;", "https://example.com/a.png?x=&copy;"),
        ('images/figure"draft".png', "images/figure%22draft%22.png"),
    ],
)
def test_image_destinations_preserve_urls_without_breaking_markdown(url: str, expected_src: str):
    element = Image("Figure", metadata=ElementMetadata(image_url=url))

    image = rendered_image(element_to_md(element))

    assert image["src"] == expected_src
    assert image["alt"] == "Figure"
    assert element.metadata.image_url == url


@pytest.mark.parametrize("mime_type", ["image/png", None])
def test_embedded_images_escape_captions_and_keep_priority_over_external_urls(
    mime_type: str | None,
):
    caption = "Unmatched ] and &amp;"
    element = Image(
        caption,
        metadata=ElementMetadata(
            image_base64="YWJjZA==",
            image_mime_type=mime_type,
            image_url="https://example.com/other.png",
        ),
    )

    image = rendered_image(element_to_md(element))

    assert image["alt"] == caption
    assert image["src"] == f"data:{mime_type or 'image/*'};base64,YWJjZA=="
    assert element.metadata.image_base64 == "YWJjZA=="


def test_excluding_binary_images_uses_the_escaped_external_destination():
    element = Image(
        "Figure ]",
        metadata=ElementMetadata(
            image_base64="YWJjZA==", image_mime_type="image/png", image_url="images/a(b.png"
        ),
    )

    image = rendered_image(element_to_md(element, exclude_binary_image_data=True))

    assert image["src"] == "images/a%28b.png"
    assert image["alt"] == "Figure ]"


@pytest.mark.parametrize("has_binary", [False, True])
def test_images_without_an_included_source_keep_the_plain_text_fallback(has_binary: bool):
    caption = "Caption [with] **literal** markers"
    element = Image(
        caption, metadata=ElementMetadata(image_base64="YWJjZA==" if has_binary else None)
    )

    assert element_to_md(element, exclude_binary_image_data=True) == caption


def test_plain_image_markdown_stays_unchanged():
    element = Image("Figure", metadata=ElementMetadata(image_url="https://example.com/figure.png"))

    assert element_to_md(element) == "![Figure](https://example.com/figure.png)"


@pytest.mark.parametrize("exporter", [elements_to_md, create_file_from_elements])
def test_document_exports_write_the_same_safe_image_markdown(exporter, tmp_path: Path):
    element = Image("Value ]", metadata=ElementMetadata(image_url="images/figure(one.png"))
    elements = [Title("Document"), element, NarrativeText("After the image.")]
    output_path = tmp_path / "document.md"

    output = exporter(iter(elements), filename=str(output_path))

    assert output_path.read_text() == output
    image = rendered_image(output)
    assert image["alt"] == element.text
    assert image["src"] == "images/figure%28one.png"
    assert "After the image." in BeautifulSoup(markdown(output), "html.parser").get_text()
