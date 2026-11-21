"""Opt-in materialization of authored form values for document extraction."""

from lxml import etree

_TEXT_INPUT_TYPES = frozenset(
    (
        "text",
        "search",
        "email",
        "tel",
        "url",
        "number",
        "date",
        "time",
        "datetime-local",
        "month",
        "week",
    )
)


def _selected_labels(select: etree._Element) -> str:
    options = list(select.iter("option"))
    selected = [option for option in options if "selected" in option.attrib]
    try:
        size = int(select.get("size", "1"))
    except ValueError:
        size = 1
    if "multiple" not in select.attrib:
        if selected:
            selected = selected[-1:]
        elif size <= 1:
            selected = [
                option
                for option in options
                if "disabled" not in option.attrib
                and not any(
                    "disabled" in group.attrib for group in option.iterancestors("optgroup")
                )
            ][:1]
    return "; ".join(
        " ".join((option.get("label") or "".join(option.itertext())).split()) for option in selected
    )


def materialize_form_values(html: str) -> str:
    """Replace form controls with static text while preserving their place in the document.

    Only authored values are available; script state, placeholder prompts, passwords and
    non-text controls are not extracted. The source HTML is unchanged. Reparse the serialized
    result with the chosen partitioner so replacement tags receive its normal element classes.
    """
    parser = etree.HTMLParser(remove_comments=True)
    try:
        root = etree.fromstring(html, parser)
    except ValueError:
        root = etree.fromstring(html.encode("utf-8"), parser)
    if root is None:
        return html
    for node in list(root.iter("form", "label", "input", "textarea", "select")):
        if any("hidden" in ancestor.attrib for ancestor in (node, *node.iterancestors())):
            text = ""
        elif node.tag in {"form", "label"}:
            node.tag = "div" if node.tag == "form" else "span"
            continue
        elif node.tag == "input":
            text = (
                node.get("value", "")
                if node.get("type", "text").lower() in _TEXT_INPUT_TYPES
                else ""
            )
        elif node.tag == "select":
            text = _selected_labels(node)
        else:
            text = "".join(node.itertext())
        node.tag = "span"
        node.attrib.clear()
        node[:] = []
        node.text = text
    return etree.tostring(root, encoding="unicode", method="html")
