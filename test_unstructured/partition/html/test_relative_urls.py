from types import SimpleNamespace

import pytest

from unstructured.partition.html import partition_html


@pytest.mark.parametrize("parser_version", ["v1", "v2"])
def test_opt_in_resolves_links_using_the_document_base(parser_version):
    elements = partition_html(
        text='<head><base href="https://example.com/docs/"></head>'
        '<body class="Document"><div class="Page"><p class="NarrativeText">'
        '<a href="../guide?q=1#section">Guide</a></p></div></body>',
        resolve_relative_urls=True,
        html_parser_version=parser_version,
        languages=["eng"],
    )

    element = next(e for e in elements if e.text == "Guide")
    if parser_version == "v1":
        assert element.metadata.link_urls == ["https://example.com/guide?q=1#section"]
    else:
        assert 'href="https://example.com/guide?q=1#section"' in element.metadata.text_as_html


def test_url_input_resolves_against_the_final_response_url(monkeypatch):
    from unstructured.partition.html import partition as module

    monkeypatch.setattr(
        module,
        "safe_get",
        lambda *args, **kwargs: SimpleNamespace(
            ok=True,
            headers={"Content-Type": "text/html"},
            url="https://example.com/final/article/",
            text='<p><a href="../source">Source</a></p>',
        ),
    )

    element = partition_html(
        url="https://example.com/old", resolve_relative_urls=True, languages=["eng"]
    )[0]

    assert element.metadata.link_urls == ["https://example.com/final/source"]


def test_resolution_uses_only_the_first_base_and_keeps_absolute_schemes():
    elements = partition_html(
        text='<head><base href="https://example.com/a/"><base href="https://other.test/"></head>'
        '<body><p><a href="page">Page</a> <a href="mailto:a@example.com">Mail</a></p>'
        '<img src="../image.png" alt="Image"></body>',
        resolve_relative_urls=True,
        languages=["eng"],
    )

    assert elements[0].metadata.link_urls == ["https://example.com/a/page", "mailto:a@example.com"]
    assert elements[1].metadata.image_url == "https://example.com/image.png"


@pytest.mark.parametrize("resolve", [False, True])
def test_without_a_base_url_relative_links_remain_relative(resolve):
    element = partition_html(
        text='<p><a href="source">Source</a></p>',
        resolve_relative_urls=resolve,
        languages=["eng"],
    )[0]
    assert element.metadata.link_urls == ["source"]


def test_existing_default_keeps_relative_link_values():
    element = partition_html(
        text='<base href="https://example.com/"><p><a href="source">Source</a></p>',
        languages=["eng"],
    )[0]
    assert element.metadata.link_urls == ["source"]
