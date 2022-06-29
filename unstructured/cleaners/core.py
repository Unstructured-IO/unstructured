import sys
import unicodedata
from unstructured.nlp.patterns import UNICODE_BULLETS_RE
import re


def clean_bullets(text) -> str:
    """Cleans unicode bullets from a section of text.

    Example
    -------
    ●  This is an excellent point! -> This is an excellent point!
    """
    search = UNICODE_BULLETS_RE.match(text)
    if search is None:
        return text

    cleaned_text = UNICODE_BULLETS_RE.sub("", text, 1)
    return cleaned_text.strip()


# TODO(robinson) - There's likely a cleaner was to accomplish this and get all of the
# unicode chracters instead of just the quotes. Doing this for now since quotes are
# an issue that are popping up in the SEC filings tests
def replace_unicode_quotes(text) -> str:
    """Replaces unicode bullets in text with the expected character

    Example
    -------
    \x93What a lovely quote!\x94 -> “What a lovely quote!”
    """
    text = text.replace("\x91", "‘")
    text = text.replace("\x92", "’")
    text = text.replace("\x93", "“")
    text = text.replace("\x94", "”")
    return text


tbl = dict.fromkeys(
    i for i in range(sys.maxunicode) if unicodedata.category(chr(i)).startswith("P")
)


def remove_punctuation(s: str) -> str:
    """Removes punctuation from a given string."""
    s = s.translate(tbl)
    return s


def clean_extra_whitespace(text: str) -> str:
    """Cleans extra whitespace characters that appear between words.

    Example
    -------
    ITEM 1.     BUSINESS -> ITEM 1. BUSINESS
    """
    cleaned_text = re.sub(r"[\xa0\n]", " ", text)
    cleaned_text = re.sub(r"([ ]{2,})", " ", cleaned_text)
    return cleaned_text.strip()


def clean_dashes(text: str) -> str:
    """Cleans dash characters in text.

    Example
    -------
    ITEM 1. -BUSINESS -> ITEM 1.  BUSINESS
    """
    # NOTE(Yuming): '\u2013' is the unicode string of 'EN DASH', a variation of "-"
    return re.sub(r"[-\u2013]", " ", text).strip()


def clean_trailing_punctuation(text: str) -> str:
    """Clean all trailing punctuation in text

    Example
    -------
    ITEM 1.     BUSINESS. -> ITEM 1.     BUSINESS
    """
    return text.strip().rstrip(".,:;")


def clean(
    text: str,
    extra_whitespace: bool = False,
    dashes: bool = False,
    bullets: bool = False,
    trailing_punctuation: bool = False,
    lowercase: bool = False,
) -> str:
    """Cleans text.

    Input
    -------
    extra_whitespace: Whether to clean extra whitespace characters in text.
    dashes: Whether to clean dash characters in text.
    bullets: Whether to clean unicode bullets from a section of text.
    trailing_punctuation: Whether to clean all trailing punctuation in text.
    lowercase: Whether to return lowercase text.
    """

    cleaned_text = text.lower() if lowercase else text
    cleaned_text = (
        clean_trailing_punctuation(cleaned_text) if trailing_punctuation else cleaned_text
    )
    cleaned_text = clean_dashes(cleaned_text) if dashes else cleaned_text
    cleaned_text = clean_extra_whitespace(cleaned_text) if extra_whitespace else cleaned_text
    cleaned_text = clean_bullets(cleaned_text) if bullets else cleaned_text
    return cleaned_text.strip()
