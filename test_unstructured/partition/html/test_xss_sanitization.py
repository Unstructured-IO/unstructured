"""End-to-end regression tests for the stored-XSS fix (GHSA-v5mq-3xhg-98m9).

These exercise the two production sinks:

* ``elements_to_html`` — the assembled HTML document,
* ``ElementMetadata.text_as_html`` — which some callers return to clients verbatim,

feeding them the exact proof-of-concept from the advisory and asserting every
vector is neutralized, while legitimate formatting is preserved.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from unstructured.documents.elements import ElementMetadata, Text
from unstructured.partition.html import partition_html
from unstructured.partition.html.convert import elements_to_html

# -- The advisory's proof-of-concept document. --
MALICIOUS_HTML = (
    '<body class="Document">'
    '<p class="Paragraph" onmouseover="alert(1)">hello'
    '<img src=x onerror="alert(document.domain)"></p>'
    '<a class="Hyperlink" href="javascript:alert(document.cookie)">click me</a>'
    "</body>"
)


def _partition_v2(html_text: str):
    return list(partition_html(text=html_text, html_parser_version="v2"))


def _all_text_as_html(elements) -> str:
    return " ".join(e.metadata.text_as_html or "" for e in elements)


def _href_values(html: str) -> list[str]:
    return [
        str(anchor["href"])
        for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True)
    ]


class DescribeElementsToHtmlIsInert:
    """The four advisory vectors must not survive into elements_to_html output."""

    def it_strips_event_handler_attributes(self):
        out = elements_to_html(_partition_v2(MALICIOUS_HTML), no_group_by_page=True)
        assert "onmouseover" not in out
        assert "onerror" not in out
        assert "onload" not in out

    def it_neutralizes_javascript_hrefs(self):
        out = elements_to_html(_partition_v2(MALICIOUS_HTML), no_group_by_page=True)
        assert "javascript:" not in out.lower()

    def it_has_no_live_svg_from_attribute_breakout(self):
        # -- title='"><svg onload=...>' must not break out of the quoted value --
        breakout = (
            '<body class="Document">'
            '<p class="Paragraph" title=\'"><svg onload=alert(1)>\'>x</p>'
            "</body>"
        )
        out = elements_to_html(_partition_v2(breakout), no_group_by_page=True)
        # -- no live <svg> tag; the payload is escaped to inert text --
        assert not re.search(r"<svg", out)
        assert "&lt;svg" in out

    def it_adds_safe_rel_for_blank_targets(self):
        blank_target = (
            '<body class="Document">'
            '<a class="Hyperlink" href="https://example.com" target="_blank">x</a>'
            "</body>"
        )
        out = elements_to_html(_partition_v2(blank_target), no_group_by_page=True)
        assert 'target="_blank"' in out
        assert "noopener" in out
        assert "noreferrer" in out

    def it_filters_overlay_styles(self):
        styled = (
            '<body class="Document">'
            '<p class="Paragraph" style="position:fixed;inset:0;z-index:9999;color:red">x</p>'
            "</body>"
        )
        out = elements_to_html(_partition_v2(styled), no_group_by_page=True)
        assert "position" not in out
        assert "inset" not in out
        assert "z-index" not in out
        assert "color:red" in out


class DescribeTextAsHtmlIsInert:
    """`text_as_html` is a value some callers return to clients directly."""

    def it_strips_event_handlers_from_text_as_html(self):
        tah = _all_text_as_html(_partition_v2(MALICIOUS_HTML))
        assert "onmouseover" not in tah
        assert "onerror" not in tah

    def it_neutralizes_javascript_hrefs_in_text_as_html(self):
        tah = _all_text_as_html(_partition_v2(MALICIOUS_HTML))
        assert "javascript:" not in tah.lower()

    def it_escapes_the_attribute_breakout_quote(self):
        breakout = (
            '<body class="Document">'
            '<p class="Paragraph" title=\'"><svg onload=alert(1)>\'>x</p>'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(breakout))
        # -- the double-quote that would break out is encoded --
        assert "&quot;" in tah
        assert "&lt;svg" in tah
        assert not re.search(r"<svg", tah)

    def it_drops_meta_refresh_attributes_from_text_as_html(self):
        meta_refresh = (
            '<body class="Document">'
            '<meta class="Keywords" http-equiv="refresh" content="0;url=javascript:alert(1)">'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(meta_refresh))
        assert "http-equiv" not in tah
        assert "refresh" not in tah

    def it_drops_form_navigation_attributes_from_text_as_html(self):
        form_payload = (
            '<body class="Document">'
            '<form class="Form" action="javascript:alert(1)">'
            '<input class="FormFieldValue" value="x" formaction="javascript:alert(2)">'
            "</form>"
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(form_payload))
        assert "action=" not in tah
        assert "formaction" not in tah
        assert "javascript:" not in tah.lower()

    def it_drops_srcset_from_text_as_html(self):
        srcset_payload = (
            '<body class="Document">'
            '<img class="Image" src="https://example.com/ok.png" '
            'srcset="javascript:alert(1) 1x">'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(srcset_payload))
        assert "srcset" not in tah
        assert "javascript:" not in tah.lower()

    def it_rejects_svg_data_images_in_text_as_html(self):
        svg_payload = (
            '<body class="Document">'
            '<img class="Image" src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=">'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(svg_payload))
        assert "data:image/svg" not in tah

    def it_adds_safe_rel_for_blank_targets_in_text_as_html(self):
        blank_target = (
            '<body class="Document">'
            '<a class="Hyperlink" href="https://example.com" target="_blank">x</a>'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(blank_target))
        assert 'target="_blank"' in tah
        assert "noopener" in tah
        assert "noreferrer" in tah

    def it_filters_overlay_styles_in_text_as_html(self):
        styled = (
            '<body class="Document">'
            '<p class="Paragraph" style="position:fixed;inset:0;z-index:9999;color:red">x</p>'
            "</body>"
        )
        tah = _all_text_as_html(_partition_v2(styled))
        assert "position" not in tah
        assert "inset" not in tah
        assert "z-index" not in tah
        assert "color: red" in tah


class DescribeLinkUrlInjectionViaMetadata:
    """`elements_to_html` builds `href` from `metadata.url` outside the ontology
    emitter, so the nh3 sweep must cover it too."""

    def it_drops_a_javascript_url_from_link_metadata(self):
        el = Text(
            text="click me",
            metadata=ElementMetadata(url="javascript:alert(1)"),
        )
        el.category = "Link"  # type: ignore[assignment]
        out = elements_to_html([el], no_group_by_page=True)
        assert "javascript:" not in out.lower()

    def it_keeps_an_https_url_from_link_metadata(self):
        el = Text(
            text="click me",
            metadata=ElementMetadata(url="https://example.com"),
        )
        el.category = "Link"  # type: ignore[assignment]
        out = elements_to_html([el], no_group_by_page=True)
        hrefs = _href_values(out)
        assert any(
            (p := urlparse(href)).scheme == "https" and p.hostname == "example.com"
            for href in hrefs
        )


class DescribeLegitimateFormattingPreserved:
    """The fix must not strip benign structure/formatting."""

    def it_preserves_tables_with_colspan_and_borders(self):
        tbl = (
            '<body class="Document"><table class="Table"><tbody>'
            '<tr><td colspan="2">A&amp;B</td></tr>'
            "<tr><td>1</td><td>2</td></tr></tbody></table></body>"
        )
        out = elements_to_html(_partition_v2(tbl), no_group_by_page=True)
        assert "<table" in out
        assert 'colspan="2"' in out
        # -- the ampersand text is HTML-escaped, not dropped --
        assert "A&amp;B" in out

    def it_preserves_safe_links_and_headings(self):
        doc = (
            '<body class="Document">'
            '<h1 class="Title">Heading</h1>'
            '<a class="Hyperlink" href="https://example.com/page">link</a>'
            "</body>"
        )
        out = elements_to_html(_partition_v2(doc), no_group_by_page=True)
        assert "https://example.com/page" in _href_values(out)
        assert "Heading" in out

    def it_preserves_mailto_scheme_in_text_as_html(self):
        # -- `mailto:` is a safe scheme and must survive into `text_as_html`
        # -- (a value some callers return to clients directly) --
        doc = '<body class="Document"><a class="Hyperlink" href="mailto:a@b.com">email</a></body>'
        tah = _all_text_as_html(_partition_v2(doc))
        assert "mailto:a@b.com" in tah

    def it_preserves_base64_images(self):
        img_src = "data:image/png;base64,iVBORw0KGgo="
        el = Text(text="", metadata=ElementMetadata(image_base64="iVBORw0KGgo="))
        el.category = "Image"  # type: ignore[assignment]
        el.metadata.image_mime_type = "image/png"
        out = elements_to_html([el], no_group_by_page=True)
        assert img_src in out
