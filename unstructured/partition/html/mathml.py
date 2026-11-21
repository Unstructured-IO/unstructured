"""A structural LaTeX fallback for common presentation MathML without a TeX annotation."""

from lxml import etree


def _escape(text: str) -> str:
    escapes = {"\\": r"\backslash{}", "^": r"\^{}", "~": r"\~{}"}
    escapes.update({char: "\\" + char for char in "{}_%&#$"})
    return "".join(escapes.get(char, char) for char in text)


def presentation_to_latex(node: etree._Element) -> str | None:
    """Render supported presentation constructs, or return None for an unsupported expression.

    This is a fallback for extraction, not a MathML layout engine. Unknown nodes, malformed
    arity and unhandled fraction-line semantics reject the whole expression so a paired visual
    fallback remains available. Existing TeX annotations and ``alttext`` take precedence.
    """
    tag = node.tag
    if tag in {"mi", "mn", "mo", "mtext"}:
        if len(node):
            return None
        text = _escape(node.text or "")
        return rf"\text{{{text}}}" if tag == "mtext" else text.strip()
    if tag == "mspace":
        return " "
    if tag == "semantics":
        children = [child for child in node if child.tag not in {"annotation", "annotation-xml"}]
        if len(children) != 1 or (node.text or "").strip():
            return None
        return presentation_to_latex(children[0])

    supported = {
        "math",
        "mrow",
        "mstyle",
        "mpadded",
        "mtd",
        "mfrac",
        "msqrt",
        "mroot",
        "msup",
        "msub",
        "msubsup",
        "mover",
        "munder",
        "munderover",
        "mfenced",
        "mtable",
        "mtr",
    }
    if tag not in supported:
        return None
    if (node.text or "").strip() or any((child.tail or "").strip() for child in node):
        return None
    parts = []
    for child in node:
        part = presentation_to_latex(child)
        if part is None:
            return None
        parts.append(part)
    if tag in {"math", "mrow", "mstyle", "mpadded", "mtd"}:
        return "".join(parts)
    if tag == "msqrt":
        return rf"\sqrt{{{''.join(parts)}}}"
    if tag == "mfenced":
        separators = "".join(node.get("separators", ",").split())
        inside = "".join(
            (_escape(separators[min(i - 1, len(separators) - 1)]) if i and separators else "")
            + part
            for i, part in enumerate(parts)
        )
        return _escape(node.get("open", "(")) + inside + _escape(node.get("close", ")"))
    if tag == "mtr":
        return " & ".join(parts) if all(child.tag == "mtd" for child in node) else None
    if tag == "mtable":
        if any(child.tag != "mtr" for child in node):
            return None
        return r"\begin{matrix}" + r" \\ ".join(parts) + r"\end{matrix}"
    expected_arity = 3 if tag in {"msubsup", "munderover"} else 2
    if len(parts) != expected_arity:
        return None
    base, second = parts[:2]
    if tag == "mfrac":
        if node.get("linethickness") is not None:
            return None
        return rf"\frac{{{base}}}{{{second}}}"
    if tag == "mroot":
        return rf"\sqrt[{second}]{{{base}}}"
    if tag == "msup":
        return f"{{{base}}}^{{{second}}}"
    if tag == "msub":
        return f"{{{base}}}_{{{second}}}"
    if tag == "msubsup":
        return f"{{{base}}}_{{{second}}}^{{{parts[2]}}}"
    if tag == "mover":
        return rf"\overset{{{second}}}{{{base}}}"
    if tag == "munder":
        return rf"\underset{{{second}}}{{{base}}}"
    return rf"\overset{{{parts[2]}}}{{\underset{{{second}}}{{{base}}}}}"
