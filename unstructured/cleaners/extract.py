import re


def _get_indexed_match(text: str, pattern: str, index: int = 0) -> re.Match:
    if not isinstance(index, int) or index < 0:
        raise ValueError(f"The index is {index}. Index must be a non-negative integer.")

    regex_match = None
    for i, result in enumerate(re.finditer(pattern, text)):
        if i == index:
            regex_match = result

    if regex_match is None:
        raise ValueError(f"Result with index {index} was not found. The largest index was {i}.")

    return regex_match


def extract_text_before(text: str, pattern: str, index: int = 0, strip: bool = True) -> str:
    """Extracts texts that occurs before the specified pattern. By default, it will use
    the first occurence of the pattern (index 0). Use the index kwarg to choose a different
    index.

    Input
    -----
    strip: If True, removes trailing whitespace from the extracted string
    """
    regex_match = _get_indexed_match(text, pattern, index)
    start, _ = regex_match.span()
    before_text = text[:start]
    return before_text.rstrip() if strip else before_text


def extract_text_after(text: str, pattern: str, index: int = 0, strip: bool = True) -> str:
    """Extracts texts that occurs before the specified pattern. By default, it will use
    the first occurence of the pattern (index 0). Use the index kwarg to choose a different
    index.

    Input
    -----
    strip: If True, removes leading whitespace from the extracted string
    """
    regex_match = _get_indexed_match(text, pattern, index)
    _, end = regex_match.span()
    before_text = text[end:]
    return before_text.lstrip() if strip else before_text
