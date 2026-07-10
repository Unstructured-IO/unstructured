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
  which drops ``javascript:`` / ``vbscript:`` and every ``data:`` URI except
  ``data:image/*`` (needed for legitimately embedded base64 images).

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

# -- Attribute names carrying a URL; their values are scheme-filtered. --
URL_ATTRIBUTES: frozenset[str] = frozenset({"href", "src", "xlink:href", "data-src", "poster"})

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
# -- but further restricted to ``data:image/*`` by :func:`is_safe_url` / the nh3
# -- attribute filter; relative URLs (no scheme) are always allowed. --
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto", "tel", "data"})

# -- Valid HTML/XML attribute name (prevents attribute-name breakout on emit). --
_ATTRIBUTE_NAME_RE = re.compile(r"^[a-zA-Z_:][-a-zA-Z0-9_:.]*$")

# -- Matches a leading ``scheme:`` ignoring surrounding whitespace and embedded
# -- control chars that browsers strip (e.g. ``java\tscript:``). --
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")


def _normalize_url(value: str) -> str:
    """Lower-case and strip whitespace/control chars a browser would ignore."""
    return re.sub(r"[\x00-\x20]+", "", value).lower()


def is_safe_url(value: str) -> bool:
    """True if ``value`` is safe to keep in a URL-bearing attribute.

    Relative URLs (no scheme) are allowed. Absolute URLs are allowed only for
    :data:`ALLOWED_URL_SCHEMES`, and ``data:`` is further narrowed to
    ``data:image/*`` so embedded base64 images survive while ``data:text/html``
    (script-executable in some contexts) is rejected.
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
        return normalized.startswith("data:image/")
    return True


def is_event_handler_attribute(name: str) -> bool:
    """True for ``on*`` event-handler attribute names (onerror, onload, ...)."""
    return name.strip().lower().startswith("on")


def sanitize_attributes(
    attributes: dict[str, object],
) -> dict[str, object]:
    """Filter an attribute mapping for safe emission (does NOT html-escape).

    Drops event-handler (``on*``) attributes, attribute names that aren't valid
    HTML attribute names, and URL-bearing attributes whose value uses an unsafe
    scheme. Values are returned unchanged; the emitter is responsible for
    ``html.escape``-ing them so escaping happens exactly once.
    """
    safe: dict[str, object] = {}
    for key, value in attributes.items():
        name = str(key).strip()
        lowered = name.lower()
        if is_event_handler_attribute(lowered):
            continue
        if not _ATTRIBUTE_NAME_RE.match(name):
            continue
        if lowered in URL_ATTRIBUTES and value is not None:
            candidate = value[0] if isinstance(value, list) and value else value
            if isinstance(candidate, str) and not is_safe_url(candidate):
                continue
        safe[key] = value
    return safe


def is_safe_tag(tag_name: str | None) -> bool:
    """True if ``tag_name`` is in the emit allowlist."""
    return bool(tag_name) and tag_name.strip().lower() in ALLOWED_TAGS


def _nh3_attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    """nh3 per-attribute hook: drop event handlers and unsafe URL values."""
    if is_event_handler_attribute(attribute):
        return None
    if attribute.lower() in URL_ATTRIBUTES and not is_safe_url(value):
        return None
    return value


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
    return nh3.clean(
        html_fragment,
        tags=set(ALLOWED_TAGS),
        attributes=attributes,
        url_schemes=set(ALLOWED_URL_SCHEMES),
        generic_attribute_prefixes=set(_GENERIC_ATTRIBUTE_PREFIXES),
        attribute_filter=_nh3_attribute_filter,
        link_rel=None,
        strip_comments=True,
    )
