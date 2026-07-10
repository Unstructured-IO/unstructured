"""Central HTML output-sanitization policy for the ontology (v2) HTML path.

`unstructured` renders untrusted document content into HTML in two places:

* ``OntologyElement.to_html`` (``documents/ontology.py``), which fills
  ``ElementMetadata.text_as_html``. Some callers return this value to clients
  verbatim, so it must be safe on its own.
* ``elements_to_html`` (``partition/html/convert.py``), which assembles a full
  HTML document from a list of elements.

Both used to interpolate attacker-controlled text, attribute names, attribute
values, and URL schemes with no output encoding, allowing stored XSS
(GHSA-v5mq-3xhg-98m9). This module is the single source of truth for the
sanitization policy shared by both paths:

* an allowlist of HTML tags we ever legitimately emit,
* an allowlist of attribute names (event-handler ``on*`` attributes are never
  allowed, killing ``onerror``/``onload``/``onmouseover``),
* a URL-scheme allowlist for URL-bearing attributes (``href``/``src``/...),
  which drops ``javascript:`` / ``vbscript:`` and permits ``data:`` only for
  raster image MIME types on ``img[src]``.

The emitter (``ontology.py``) uses the lightweight filters here plus
``html.escape`` to make ``text_as_html`` safe on its own; ``elements_to_html``
additionally runs the assembled document through :func:`sanitize_html_fragment`
(``nh3``) as defense-in-depth that also covers attributes it injects itself
(e.g. ``href`` from ``metadata.url``).
"""

from __future__ import annotations

import re

import nh3

# -- Tags the ontology / convert paths legitimately emit. Anything outside this
# -- set (``<script>``, ``<iframe>``, ...) is dropped/neutralized. --
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        # layout / structural
        "body",
        "div",
        "section",
        "header",
        "footer",
        "aside",
        "nav",
        "figure",
        "figcaption",
        "hr",
        "br",
        # text
        "span",
        "p",
        "blockquote",
        "pre",
        "address",
        "time",
        "mark",
        "ins",
        "del",
        "cite",
        "sub",
        "sup",
        "b",
        "i",
        "s",
        "code",
        # headings
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        # lists
        "ul",
        "ol",
        "li",
        "dl",
        # tables
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        # links / media
        "a",
        "img",
        "svg",
        "audio",
        "video",
        # forms
        "form",
        "input",
        "label",
        "button",
        # misc content
        "math",
        "meta",
    }
)

# -- Attribute names carrying a URL; their values are scheme-filtered. Keep this
# -- list broader than the attributes we currently allow so newly-allowed URL
# -- attributes are scheme-checked by default. --
URL_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "action",
        "cite",
        "data-src",
        "formaction",
        "href",
        "poster",
        "src",
        "srcset",
        "xlink:href",
    }
)

# -- Data URLs are only needed for embedded image bytes. SVG is intentionally
# -- excluded because SVG documents can carry active content in some render
# -- contexts. --
ALLOWED_DATA_IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/avif",
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/x-icon",
    }
)

# -- Inline CSS is untrusted too. Keep only inert presentation properties that
# -- preserve existing table/background formatting and reject layout/overlay
# -- controls like position/inset/z-index.
ALLOWED_CSS_PROPERTIES: frozenset[str] = frozenset(
    {
        "background-color",
        "border",
        "border-bottom",
        "border-collapse",
        "border-color",
        "border-left",
        "border-right",
        "border-style",
        "border-top",
        "border-width",
        "color",
        "font-style",
        "font-weight",
        "text-align",
        "text-decoration",
        "vertical-align",
        "white-space",
    }
)

# -- Attributes allowed on every tag. --
_GLOBAL_ATTRIBUTES: frozenset[str] = frozenset(
    {"class", "id", "style", "title", "dir", "lang", "role", "name", "align"}
)

# -- Per-tag attributes in addition to the global set. --
_TAG_ATTRIBUTES: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "target", "rel"}),
    "img": frozenset({"src", "alt", "width", "height"}),
    "svg": frozenset({"src", "alt", "width", "height", "xlink:href"}),
    "audio": frozenset({"src", "controls"}),
    "video": frozenset({"src", "controls", "poster", "width", "height"}),
    "input": frozenset({"type", "checked", "value", "placeholder"}),
    "td": frozenset({"colspan", "rowspan", "headers", "scope"}),
    "th": frozenset({"colspan", "rowspan", "headers", "scope"}),
    "ol": frozenset({"start", "type"}),
    "label": frozenset({"for"}),
    "meta": frozenset({"charset", "content"}),
    "time": frozenset({"datetime"}),
}

# -- Attribute-name prefixes allowed on any tag (data-page-number, aria-*, ...). --
_GENERIC_ATTRIBUTE_PREFIXES: frozenset[str] = frozenset({"data-", "aria-"})

# -- URL schemes permitted on URL-bearing attributes. ``data`` is permitted here
# -- but further restricted to raster image MIME types on ``img[src]`` by
# -- :func:`is_safe_url` / the nh3 attribute filter; relative URLs (no scheme)
# -- are always allowed. --
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto", "tel", "data"})

# -- Valid HTML/XML attribute name (prevents attribute-name breakout on emit). --
_ATTRIBUTE_NAME_RE = re.compile(r"^[a-zA-Z_:][-a-zA-Z0-9_:.]*$")

# -- Matches a leading ``scheme:`` ignoring surrounding whitespace and embedded
# -- control chars that browsers strip (e.g. ``java\tscript:``). --
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

_REQUIRED_BLANK_TARGET_REL_VALUES: frozenset[str] = frozenset({"noopener", "noreferrer"})

# -- Match an anchor start tag and detect `target="_blank"` / an existing `rel`
# -- so we can add reverse-tabnabbing protection to new-tab links only. nh3's
# -- output is well-formed (attribute values are escaped, so `>` never appears
# -- inside one), which makes matching whole start tags with a regex safe. --
_ANCHOR_START_TAG_RE = re.compile(r"<a\b[^>]*>", flags=re.IGNORECASE)
_BLANK_TARGET_RE = re.compile(r"""\btarget\s*=\s*["']?_blank\b""", flags=re.IGNORECASE)
_REL_ATTRIBUTE_RE = re.compile(r"""\brel\s*=""", flags=re.IGNORECASE)

_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", flags=re.DOTALL)
_CSS_UNSAFE_VALUE_RE = re.compile(
    r"(@import|expression\s*\(|url\s*\(|javascript:|vbscript:|data:|-moz-binding|behavior\s*:)",
    flags=re.IGNORECASE,
)


def _normalize_url(value: str) -> str:
    """Lower-case and strip whitespace/control chars a browser would ignore."""
    return re.sub(r"[\x00-\x20]+", "", value).lower()


def _normalized_tag_and_attribute(
    tag_name: str | None = None,
    attribute_name: str | None = None,
) -> tuple[str | None, str | None]:
    tag = tag_name.strip().lower() if tag_name else None
    attribute = attribute_name.strip().lower() if attribute_name else None
    return tag, attribute


def _is_allowed_data_image_url(
    normalized_value: str,
    *,
    tag_name: str | None = None,
    attribute_name: str | None = None,
) -> bool:
    tag, attribute = _normalized_tag_and_attribute(tag_name, attribute_name)
    if tag != "img" or attribute != "src":
        return False
    if not normalized_value.startswith("data:") or "," not in normalized_value:
        return False
    media_type = normalized_value[5:].split(",", 1)[0].split(";", 1)[0]
    return media_type in ALLOWED_DATA_IMAGE_MIME_TYPES


def is_safe_url(
    value: str,
    *,
    tag_name: str | None = None,
    attribute_name: str | None = None,
) -> bool:
    """True if ``value`` is safe to keep in a URL-bearing attribute.

    Relative URLs (no scheme) are allowed. Absolute URLs are allowed only for
    :data:`ALLOWED_URL_SCHEMES`, and ``data:`` is further narrowed to raster
    image MIME types on ``img[src]`` so embedded base64 images survive while
    SVG / HTML / JavaScript data documents are rejected.
    """
    normalized = _normalize_url(value)
    match = _SCHEME_RE.match(normalized)
    if match is None:
        # -- no scheme -> relative URL (or a fragment/anchor); safe --
        return True
    scheme = match.group(1)
    if scheme not in ALLOWED_URL_SCHEMES:
        return False
    if scheme == "data":
        return _is_allowed_data_image_url(
            normalized,
            tag_name=tag_name,
            attribute_name=attribute_name,
        )
    return True


def is_event_handler_attribute(name: str) -> bool:
    """True for ``on*`` event-handler attribute names (onerror, onload, ...)."""
    return name.strip().lower().startswith("on")


def _is_allowed_attribute_for_tag(name: str, tag_name: str | None) -> bool:
    lowered = name.lower()
    if any(lowered.startswith(prefix) for prefix in _GENERIC_ATTRIBUTE_PREFIXES):
        return True

    allowed_attributes = set(_GLOBAL_ATTRIBUTES)
    if tag_name:
        allowed_attributes.update(_TAG_ATTRIBUTES.get(tag_name.strip().lower(), frozenset()))
    return lowered in allowed_attributes


def _link_rel_with_required_values(value: object | None) -> str:
    existing_values = str(value or "").split()
    existing_lowered = {rel.lower() for rel in existing_values}
    missing_values = [
        rel for rel in sorted(_REQUIRED_BLANK_TARGET_REL_VALUES) if rel not in existing_lowered
    ]
    return " ".join([*existing_values, *missing_values]).strip()


def sanitize_style_attribute(value: object) -> str:
    """Return a style attribute containing only safe presentation declarations."""
    style = _CSS_COMMENT_RE.sub("", str(value))
    safe_declarations: list[str] = []
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        raw_property, raw_value = declaration.split(":", 1)
        property_name = raw_property.strip().lower()
        property_value = " ".join(raw_value.strip().split())
        if property_name not in ALLOWED_CSS_PROPERTIES:
            continue
        if not property_value or _CSS_UNSAFE_VALUE_RE.search(property_value):
            continue
        safe_declarations.append(f"{property_name}: {property_value}")
    return "; ".join(safe_declarations)


def sanitize_attributes(
    attributes: dict[str, object],
    tag_name: str | None = None,
) -> dict[str, object]:
    """Filter an attribute mapping for safe emission (does NOT html-escape).

    Drops event-handler (``on*``) attributes, attribute names that aren't valid
    HTML attribute names, attributes not allowed for ``tag_name``, and URL-bearing
    attributes whose value uses an unsafe scheme. Values are returned unchanged;
    the emitter is responsible for ``html.escape``-ing them so escaping happens
    exactly once.
    """
    safe: dict[str, object] = {}
    for key, value in attributes.items():
        name = str(key).strip()
        lowered = name.lower()
        if is_event_handler_attribute(lowered):
            continue
        if not _ATTRIBUTE_NAME_RE.match(name):
            continue
        if not _is_allowed_attribute_for_tag(name, tag_name):
            continue
        if lowered == "style":
            sanitized_style = sanitize_style_attribute(value)
            if not sanitized_style:
                continue
            safe[name] = sanitized_style
            continue
        if lowered in URL_ATTRIBUTES and value is not None:
            candidate = value[0] if isinstance(value, list) and value else value
            if isinstance(candidate, str) and not is_safe_url(
                candidate,
                tag_name=tag_name,
                attribute_name=lowered,
            ):
                continue
        safe[name] = value

    if (tag_name or "").strip().lower() == "a" and str(safe.get("target", "")).lower() == "_blank":
        safe["rel"] = _link_rel_with_required_values(safe.get("rel"))

    return safe


def is_safe_tag(tag_name: str | None) -> bool:
    """True if ``tag_name`` is in the emit allowlist."""
    return bool(tag_name) and tag_name.strip().lower() in ALLOWED_TAGS


def _nh3_attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    """nh3 per-attribute hook: drop event handlers and unsafe URL values."""
    if is_event_handler_attribute(attribute):
        return None
    if attribute.lower() == "style":
        return sanitize_style_attribute(value) or None
    if attribute.lower() in URL_ATTRIBUTES and not is_safe_url(
        value,
        tag_name=tag,
        attribute_name=attribute,
    ):
        return None
    return value


def _add_rel_to_blank_target_links(html_fragment: str) -> str:
    """Add reverse-tabnabbing ``rel`` tokens to ``target="_blank"`` anchors only.

    nh3's ``link_rel`` would stamp ``rel`` onto *every* link, stripping the
    ``Referer`` header from ordinary same-tab navigation. Reverse tabnabbing is
    only a concern for new-tab links, so we scope the tokens to anchors that
    actually open a new browsing context and leave same-tab links untouched.
    """

    def add_rel(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not _BLANK_TARGET_RE.search(tag) or _REL_ATTRIBUTE_RE.search(tag):
            return tag
        rel = " ".join(sorted(_REQUIRED_BLANK_TARGET_REL_VALUES))
        return f'{tag[:-1].rstrip()} rel="{rel}">'

    return _ANCHOR_START_TAG_RE.sub(add_rel, html_fragment)


def sanitize_html_fragment(html_fragment: str) -> str:
    """Sanitize an assembled HTML fragment with ``nh3`` (defense-in-depth).

    Applies the shared tag/attribute/URL-scheme allowlists. Used on the final
    output of ``elements_to_html`` so that attributes injected outside the
    ontology emitter (e.g. an ``href`` built from ``metadata.url``) are also
    neutralized.
    """
    attributes: dict[str, set[str]] = {"*": set(_GLOBAL_ATTRIBUTES)}
    for tag, attrs in _TAG_ATTRIBUTES.items():
        attributes[tag] = set(attrs)
    cleaned = nh3.clean(
        html_fragment,
        tags=set(ALLOWED_TAGS),
        attributes=attributes,
        url_schemes=set(ALLOWED_URL_SCHEMES),
        generic_attribute_prefixes=set(_GENERIC_ATTRIBUTE_PREFIXES),
        filter_style_properties=set(ALLOWED_CSS_PROPERTIES),
        attribute_filter=_nh3_attribute_filter,
        # -- Scope reverse-tabnabbing `rel` tokens to `_blank` anchors ourselves
        # -- rather than letting nh3 add them to every link (which would strip
        # -- the Referer header from same-tab navigation). --
        link_rel=None,
        strip_comments=True,
    )
    return _add_rel_to_blank_target_links(cleaned)
