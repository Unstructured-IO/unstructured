import datetime
import re
from typing import List, Optional

from unstructured.nlp.patterns import (
    EMAIL_ADDRESS_PATTERN,
    EMAIL_DATETIMETZ_PATTERN,
    IMAGE_URL_PATTERN,
    IP_ADDRESS_NAME_PATTERN,
    IP_ADDRESS_PATTERN_RE,
    MAPI_ID_PATTERN,
    US_PHONE_NUMBERS_RE,
)


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
    the first occurrence of the pattern (index 0). Use the index kwarg to choose a different
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
    the first occurrence of the pattern (index 0). Use the index kwarg to choose a different
    index.

    Input
    -----
    strip: If True, removes leading whitespace from the extracted string
    """
    regex_match = _get_indexed_match(text, pattern, index)
    _, end = regex_match.span()
    before_text = text[end:]
    return before_text.lstrip() if strip else before_text


def extract_email_address(text: str) -> List[str]:
    return re.findall(EMAIL_ADDRESS_PATTERN, text.lower())


def extract_ip_address(text: str) -> List[str]:
    return re.findall(IP_ADDRESS_PATTERN_RE, text)


def extract_ip_address_name(text: str) -> List[str]:
    return re.findall(IP_ADDRESS_NAME_PATTERN, text)


def extract_mapi_id(text: str) -> List[str]:
    mapi_ids = re.findall(MAPI_ID_PATTERN, text)
    mapi_ids = [mid.replace(";", "") for mid in mapi_ids]
    return mapi_ids


def extract_datetimetz(text: str) -> Optional[datetime.datetime]:
    date_extractions = re.findall(EMAIL_DATETIMETZ_PATTERN, text)
    if len(date_extractions) > 0:
        return datetime.datetime.strptime(date_extractions[0], "%a, %d %b %Y %H:%M:%S %z")
    else:
        return None


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


def extract_ordered_bullets(text) -> tuple:
    """Extracts the start of bulleted text sections bullets
    accounting numeric and alphanumeric types.

    Output
    -----
    tuple(section, sub_section, sub_sub_section): Each bullet partition
    is a string or None if not present.

    Example
    -------
    This is a very important point -> (None, None, None)
    1.1 This is a very important point -> ("1", "1", None)
    a.1 This is a very important point -> ("a", "1", None)
    """
    a, b, c, temp = None, None, None, None
    text_sp = text.split()
    if any(["." not in text_sp[0], ".." in text_sp[0]]):
        return a, b, c

    bullet = re.split(pattern=r"[\.]", string=text_sp[0])
    if not bullet[-1]:
        del bullet[-1]

    if len(bullet[0]) > 2:
        return a, b, c

    a, *temp = bullet
    if temp:
        try:
            b, c, *_ = temp
        except ValueError:
            b = temp
        b = "".join(b)
        c = "".join(c) if c else None
    return a, b, c


def extract_image_urls_from_html(text: str) -> List[str]:
    return re.findall(IMAGE_URL_PATTERN, text)
