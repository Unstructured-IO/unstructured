"""Unit tests for the shared HTML output-sanitization policy (GHSA-v5mq-3xhg-98m9)."""

import pytest

from unstructured.documents.html_sanitization import (
    ALLOWED_URL_SCHEMES,
    is_event_handler_attribute,
    is_safe_tag,
    is_safe_url,
    sanitize_attributes,
    sanitize_html_fragment,
    sanitize_style_attribute,
)


class DescribeIsSafeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com/path?q=1",
            "mailto:user@example.com",
            "tel:+15551234",
            "/relative/path",
            "relative/path",
            "#anchor",
            "?query=only",
        ],
    )
    def it_allows_safe_urls(self, url: str):
        assert is_safe_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "JaVaScRiPt:alert(1)",
            "  javascript:alert(1)",
            "java\tscript:alert(1)",
            "java\nscript:alert(1)",
            "vbscript:msgbox(1)",
            "data:text/html,<script>alert(1)</script>",
            "data:application/javascript,alert(1)",
            "file:///etc/passwd",
        ],
    )
    def it_rejects_dangerous_urls(self, url: str):
        assert is_safe_url(url) is False

    def it_only_permits_raster_image_data_uris_on_img_src(self):
        # -- data: is in the scheme allowlist but narrowed to raster img[src] so
        # -- base64 images survive while script-executable data URIs do not --
        assert "data" in ALLOWED_URL_SCHEMES
        assert (
            is_safe_url(
                "data:image/gif;base64,R0lGOD",
                tag_name="img",
                attribute_name="src",
            )
            is True
        )
        assert (
            is_safe_url(
                "data:image/svg+xml;base64,PHN2Zz4=",
                tag_name="img",
                attribute_name="src",
            )
            is False
        )
        assert (
            is_safe_url(
                "data:image/png;base64,iVBORw0KGgo=",
                tag_name="a",
                attribute_name="href",
            )
            is False
        )
        assert (
            is_safe_url(
                "data:text/html;base64,PHNjcmlwdD4=",
                tag_name="img",
                attribute_name="src",
            )
            is False
        )


class DescribeIsEventHandlerAttribute:
    @pytest.mark.parametrize("name", ["onerror", "onload", "onmouseover", "ONCLICK", " onfocus"])
    def it_detects_event_handlers(self, name: str):
        assert is_event_handler_attribute(name) is True

    @pytest.mark.parametrize("name", ["class", "href", "id", "data-src", "title"])
    def it_ignores_non_event_handlers(self, name: str):
        assert is_event_handler_attribute(name) is False


class DescribeIsSafeTag:
    @pytest.mark.parametrize("tag", ["div", "p", "a", "img", "table", "TD", "svg"])
    def it_allows_known_tags(self, tag: str):
        assert is_safe_tag(tag) is True

    @pytest.mark.parametrize("tag", ["script", "iframe", "object", "embed", "", None])
    def it_rejects_unknown_tags(self, tag):
        assert is_safe_tag(tag) is False


class DescribeSanitizeAttributes:
    def it_drops_event_handler_attributes(self):
        result = sanitize_attributes(
            {"onerror": "alert(1)", "onmouseover": "x", "class": "Foo"},
            tag_name="p",
        )
        assert result == {"class": "Foo"}

    def it_drops_url_attributes_with_unsafe_schemes(self):
        result = sanitize_attributes({"href": "javascript:alert(1)", "id": "x"}, tag_name="a")
        assert result == {"id": "x"}

    def it_keeps_url_attributes_with_safe_schemes(self):
        link_result = sanitize_attributes({"href": "https://example.com"}, tag_name="a")
        image_result = sanitize_attributes({"src": "/img.png"}, tag_name="img")
        assert link_result == {"href": "https://example.com"}
        assert image_result == {"src": "/img.png"}

    def it_keeps_raster_data_image_uris_on_img_src(self):
        result = sanitize_attributes({"src": "data:image/png;base64,AAAA"}, tag_name="img")
        assert result == {"src": "data:image/png;base64,AAAA"}

    def it_drops_data_image_uris_outside_img_src(self):
        result = sanitize_attributes({"href": "data:image/png;base64,AAAA"}, tag_name="a")
        assert result == {}

    def it_drops_svg_data_image_uris(self):
        result = sanitize_attributes({"src": "data:image/svg+xml;base64,PHN2Zz4="}, tag_name="img")
        assert result == {}

    def it_drops_malformed_attribute_names(self):
        # -- a name that isn't a valid HTML attribute name can't be emitted safely --
        result = sanitize_attributes({'x"><svg onload=alert(1)>': "y", "id": "ok"}, tag_name="p")
        assert result == {"id": "ok"}

    def it_drops_attributes_not_allowed_on_the_tag(self):
        result = sanitize_attributes(
            {
                "action": "https://example.com/submit",
                "class": "Form",
                "formaction": "https://example.com/button",
                "http-equiv": "refresh",
                "srcset": "https://example.com/a.png 1x",
            },
            tag_name="form",
        )
        assert result == {"class": "Form"}

    def it_allows_tag_specific_attributes(self):
        result = sanitize_attributes(
            {"colspan": "2", "rowspan": "3", "headers": "h1", "scope": "col"},
            tag_name="td",
        )
        assert result == {"colspan": "2", "rowspan": "3", "headers": "h1", "scope": "col"}

    def it_filters_inline_style_values(self):
        result = sanitize_attributes(
            {
                "style": (
                    "background-color: lightblue; position: fixed; inset: 0; "
                    "z-index: 9999; border: 1px solid black"
                )
            },
            tag_name="p",
        )
        assert result == {"style": "background-color: lightblue; border: 1px solid black"}

    def it_adds_noopener_noreferrer_for_blank_targets(self):
        result = sanitize_attributes(
            {"href": "https://example.com", "target": "_blank"},
            tag_name="a",
        )
        assert result == {
            "href": "https://example.com",
            "target": "_blank",
            "rel": "noopener noreferrer",
        }

    def it_does_not_html_escape_values(self):
        # -- escaping happens once, at emit time; values pass through untouched here --
        result = sanitize_attributes({"title": 'a & b < c "d"'}, tag_name="p")
        assert result == {"title": 'a & b < c "d"'}

    def it_scheme_filters_list_valued_url_attributes(self):
        result = sanitize_attributes({"href": ["javascript:alert(1)"]}, tag_name="a")
        assert result == {}


class DescribeSanitizeStyleAttribute:
    def it_keeps_safe_presentation_declarations(self):
        style = "background-color: lightblue; text-align: right; border-collapse: collapse"
        assert sanitize_style_attribute(style) == style

    def it_drops_layout_overlay_declarations(self):
        style = "position: fixed; inset: 0; z-index: 9999; color: red"
        assert sanitize_style_attribute(style) == "color: red"

    def it_drops_url_and_expression_values(self):
        style = "background-color: url(javascript:alert(1)); color: expression(alert(1))"
        assert sanitize_style_attribute(style) == ""


class DescribeSanitizeHtmlFragment:
    def it_strips_event_handlers(self):
        assert "onerror" not in sanitize_html_fragment('<img src="x" onerror="alert(1)">')
        assert "onmouseover" not in sanitize_html_fragment('<p onmouseover="alert(1)">hi</p>')

    def it_strips_javascript_hrefs(self):
        assert "javascript:" not in sanitize_html_fragment('<a href="javascript:alert(1)">x</a>')

    def it_removes_disallowed_tags(self):
        cleaned = sanitize_html_fragment("<script>alert(1)</script><p>ok</p>")
        assert "<script" not in cleaned
        assert "<p>" in cleaned or "ok" in cleaned

    def it_preserves_base64_image_sources(self):
        cleaned = sanitize_html_fragment('<img src="data:image/png;base64,iVBORw0KGgo=" alt="ok">')
        assert "data:image/png" in cleaned

    def it_preserves_avif_base64_image_sources(self):
        cleaned = sanitize_html_fragment('<img src="data:image/avif;base64,AAAAAA==" alt="ok">')
        assert "data:image/avif" in cleaned

    def it_drops_svg_data_image_sources(self):
        cleaned = sanitize_html_fragment(
            '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" alt="bad">'
        )
        assert "data:image/svg" not in cleaned

    def it_drops_data_image_links(self):
        cleaned = sanitize_html_fragment('<a href="data:image/png;base64,AAAA">x</a>')
        assert "data:image/png" not in cleaned

    def it_drops_non_image_data_uris(self):
        cleaned = sanitize_html_fragment('<img src="data:text/html,<script>alert(1)</script>">')
        assert "data:text/html" not in cleaned
        assert "<script" not in cleaned

    def it_adds_noopener_noreferrer_to_links(self):
        cleaned = sanitize_html_fragment('<a href="https://example.com" target="_blank">x</a>')
        assert "noopener" in cleaned
        assert "noreferrer" in cleaned

    def it_does_not_add_rel_to_same_tab_links(self):
        # -- same-tab links must keep their Referer header (no unconditional rel) --
        cleaned = sanitize_html_fragment('<a href="https://example.com">x</a>')
        assert "rel=" not in cleaned
        assert "noreferrer" not in cleaned

    def it_does_not_duplicate_rel_on_blank_target_links(self):
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_blank" rel="noopener noreferrer">x</a>'
        )
        assert cleaned.count("rel=") == 1

    def it_filters_inline_styles(self):
        cleaned = sanitize_html_fragment(
            '<p style="position:fixed;inset:0;z-index:9999;color:red">x</p>'
        )
        assert "position" not in cleaned
        assert "inset" not in cleaned
        assert "z-index" not in cleaned
        assert "color:red" in cleaned

    def it_preserves_legitimate_table_formatting(self):
        cleaned = sanitize_html_fragment(
            '<table><tr><td colspan="2" style="border: 1px solid black;">A</td></tr></table>'
        )
        assert "<table" in cleaned
        assert 'colspan="2"' in cleaned
        assert "border" in cleaned
