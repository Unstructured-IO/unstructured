import typing as t


def wrap_text(text: str, wrap_at: int, center: bool = False) -> t.List[str]:
    words = text.split()
    lines: t.List[t.List[str]] = []
    line: t.List[str] = []
    for w in words:
        if len(" ".join(line + [w])) > wrap_at:
            lines.append(line)
            line = [w]
        else:
            line.append(w)
    joined_lines: t.List[str] = [" ".join(line) for line in lines]
    if center:
        joined_lines = [" " * int((wrap_at - len(line)) / 2) + line for line in joined_lines]
    joined_lines = [line + " " * (wrap_at - len(line)) for line in joined_lines]
    return joined_lines


def print_experimental_banner():
    text = (
        "Experimental features are in the early stages of development and testing and may not have "
        "undergone the same level of scrutiny, stability, or security checks as fully supported "
        "features. They are provided for user feedback and may exhibit unexpected behaviors or "
        "limitations. We recommend using experimental features in non-production environments "
        "or for testing purposes only. Your feedback and experiences with these features are "
        "valuable for their further refinement and development. Use at your own discretion "
        "and risk."
    )
    wrap_at = 90
    lines = wrap_text(text=text, wrap_at=wrap_at)
    print("#" * 120)
    print("#" * 2 + " " * 52 + "EXPERIMENTAL" + " " * 52 + "#" * 2)
    for line in lines:
        print("#" * 2 + " " * 13 + line + " " * 13 + "#" * 2)
    print("#" * 120)
