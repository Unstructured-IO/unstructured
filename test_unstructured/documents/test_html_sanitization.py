"""Unit tests for the shared HTML output-sanitization policy (GHSA-v5mq-3xhg-98m9)."""

from html.parser import HTMLParser

import pytest

from unstructured.documents.html_sanitization import (
    ALLOWED_URL_SCHEMES,
    _add_rel_to_blank_target_links,
    is_event_handler_attribute,
    is_safe_tag,
    is_safe_url,
    sanitize_attributes,
    sanitize_html_fragment,
    sanitize_style_attribute,
)


class _AttributeCollector(HTMLParser):
    """Collect the attributes of every start tag, so tests assert on names, not text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attributes: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.attributes.append(dict(attrs))


def _all_attributes(html_fragment: str) -> list[dict[str, str | None]]:
    """Return the attributes of every start tag in ``html_fragment``."""
    collector = _AttributeCollector()
    collector.feed(html_fragment)
    return collector.attributes


def _anchor_attributes(html_fragment: str) -> dict[str, str | None]:
    """Return the attributes of the first start tag in ``html_fragment``."""
    return _all_attributes(html_fragment)[0]


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
        assert result == {
            "colspan": "2",
            "rowspan": "3",
            "headers": "h1",
            "scope": "col",
        }

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
    def it_preserves_all_table_row_group_tags(self):
        table = (
            "<table><thead><tr><th>H</th></tr></thead>"
            "<tbody><tr><td>B</td></tr></tbody>"
            "<tfoot><tr><td>F</td></tr></tfoot></table>"
        )

        assert sanitize_html_fragment(table) == table

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

    def it_completes_a_partial_rel_on_blank_target_links(self):
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_blank" rel="nofollow">x</a>'
        )
        assert 'rel="nofollow noopener noreferrer"' in cleaned

    def it_keeps_a_rel_lookalike_inside_another_attribute_value(self):
        cleaned = sanitize_html_fragment(
            '<a title="rel=\'x onmouseover=alert(1)\'" href="https://example.com"'
            ' rel="noopener noreferrer" target="_blank">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert "onmouseover" not in attributes
        # -- the label keeps its inert text and the real `rel` is left complete --
        assert attributes["title"] == "rel='x onmouseover=alert(1)'"
        assert attributes["rel"] == "noopener noreferrer"

    def it_keeps_an_entity_encoded_rel_lookalike_inside_another_attribute_value(self):
        cleaned = sanitize_html_fragment(
            '<a title="rel=&#39;x onmouseover=alert(1)&#39;" href="https://example.com"'
            ' rel="nofollow" target="_blank">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert "onmouseover" not in attributes
        assert attributes["rel"] == "nofollow noopener noreferrer"

    def it_ignores_unrelated_attributes_before_the_real_rel(self):
        cleaned = sanitize_html_fragment(
            '<a data-target="_blank" title="rel=\'x onmouseover=alert(1)\'"'
            ' href="https://example.com" target="_blank" rel="nofollow">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert "onmouseover" not in attributes
        assert attributes["data-target"] == "_blank"
        assert attributes["rel"] == "nofollow noopener noreferrer"

    def it_does_not_treat_suffixed_attribute_names_as_target_or_rel(self):
        # -- `data-target`/`aria-rel` are not the real attributes; nothing to do --
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" data-target="_blank" aria-rel="noopener">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert "rel" not in attributes
        assert "target" not in attributes

    def it_completes_rel_tokens_without_duplicating_present_ones(self):
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_BLANK" rel="NOOPENER nofollow">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        # -- present tokens are kept as written, only the missing one is added --
        assert attributes["rel"] == "NOOPENER nofollow noreferrer"

    def it_keeps_an_inert_rel_lookalike_when_serializing_elements(self):
        from unstructured.documents.elements import ElementMetadata, Text
        from unstructured.partition.html.convert import elements_to_html

        element = Text(
            text="x",
            metadata=ElementMetadata(
                text_as_html=(
                    "<a title=\"rel='x onmouseover=alert(1)'\""
                    ' href="https://example.com" target="_blank">x</a>'
                ),
                page_number=1,
            ),
        )
        cleaned = elements_to_html([element])
        anchors = [a for a in _all_attributes(cleaned) if a.get("href") == "https://example.com"]
        assert len(anchors) == 1
        assert "onmouseover" not in anchors[0]
        assert anchors[0]["rel"] == "noopener noreferrer"

    def it_adds_a_missing_rel_without_touching_the_link_text(self):
        cleaned = sanitize_html_fragment('<a href="https://example.com" target="_blank">x</a>')
        attributes = _anchor_attributes(cleaned)
        assert attributes["rel"] == "noopener noreferrer"
        # -- the closing delimiter must be emitted once: the text stays `x`, not `>x` --
        assert ">>" not in cleaned
        assert cleaned.endswith(">x</a>")

    def it_completes_an_empty_rel_value(self):
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_blank" rel="">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert attributes["rel"] == "noopener noreferrer"

    def it_does_not_treat_a_suffixed_target_value_as_blank(self):
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_blank-report">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert "rel" not in attributes

    def it_completes_a_blank_link_whose_attribute_name_holds_a_quote(self):
        # -- the quote belongs to the attribute name `data-x"`; the anchor itself is real, so
        # -- the required tokens must still be applied instead of skipping the link --
        cleaned = sanitize_html_fragment(
            '<a href="https://example.com" target="_blank" data-x"="plain">x</a>'
        )
        attributes = _anchor_attributes(cleaned)
        assert attributes["rel"] == "noopener noreferrer"
        assert not any(name.lower().startswith("on") for name in attributes)

    def it_does_not_rewrite_a_fake_anchor_inside_another_attribute_value(self):
        # -- unit level: the outer boundary is the part a scanner cannot establish, so this
        # -- checks the rewriting step itself against a fragment whose quoted value carries an
        # -- anchor-looking substring --
        fragment = "<p title=\"<a target='_blank' rel=foo onmouseover=alert(1) x>\">x</p>"
        assert _add_rel_to_blank_target_links(fragment) == fragment

    def it_keeps_a_fake_anchor_inside_another_attribute_value_inert(self):
        # -- a serializer may leave `<` and `>` literal inside a quoted value, so an
        # -- anchor-looking substring there is text, not an element: rewriting its `rel`
        # -- would close the surrounding value and expose the rest as real attributes --
        cleaned = sanitize_html_fragment(
            "<p title=\"<a target='_blank' rel=foo onmouseover=alert(1) x>\">x</p>"
        )
        assert "rel=foo" in cleaned
        assert not any(
            name.lower().startswith("on") for attrs in _all_attributes(cleaned) for name in attrs
        )
        assert "noopener" not in cleaned

    def it_does_not_treat_a_padded_target_value_as_blank(self):
        # -- `target=" _blank"` names a browsing context; only the bare keyword is reserved --
        for target in (" _blank", "_blank ", "_blank\t"):
            cleaned = sanitize_html_fragment(
                f'<a href="https://example.com" target="{target}">x</a>'
            )
            attributes = _anchor_attributes(cleaned)
            assert "rel" not in attributes, target

    def it_completes_rel_with_single_quoted_attributes(self):
        cleaned = sanitize_html_fragment(
            "<a href='https://example.com' target='_blank' rel='nofollow'>x</a>"
        )
        attributes = _anchor_attributes(cleaned)
        assert attributes["rel"] == "nofollow noopener noreferrer"

    def it_keeps_the_link_text_when_serializing_elements(self):
        from unstructured.documents.elements import ElementMetadata, Text
        from unstructured.partition.html.convert import elements_to_html

        element = Text(
            text="x",
            metadata=ElementMetadata(
                text_as_html='<a href="https://example.com" target="_blank">x</a>',
                page_number=1,
            ),
        )
        cleaned = elements_to_html([element])
        anchors = [a for a in _all_attributes(cleaned) if a.get("href") == "https://example.com"]
        assert len(anchors) == 1
        assert anchors[0]["rel"] == "noopener noreferrer"
        # -- the extra delimiter would show up as escaped text in front of the label --
        assert "&gt;" not in cleaned

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
