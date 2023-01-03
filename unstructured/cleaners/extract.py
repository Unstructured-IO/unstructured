import re

from unstructured.nlp.patterns import US_PHONE_NUMBERS_RE


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


def extract_us_phone_number(text: str):
    """Extracts a US phone number from a section of text that includes a phone number. If there
    is no phone number present, the result will be an empty string.

    Example
    -------
    extract_phone_number("Phone Number: 215-867-5309") -> "215-867-5309"
    """
    regex_match = US_PHONE_NUMBERS_RE.search(text)
    if regex_match is None:
        return ""

    start, end = regex_match.span()
    phone_number = text[start:end]
    return phone_number.strip()
