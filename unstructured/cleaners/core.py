import quopri
import re
import sys
import unicodedata

from unstructured.file_utils.encoding import (
    format_encoding_str,
)
from unstructured.nlp.patterns import (
    DOUBLE_PARAGRAPH_PATTERN_RE,
    PARAGRAPH_PATTERN,
    PARAGRAPH_PATTERN_RE,
    UNICODE_BULLETS_RE,
)


def clean_non_ascii_chars(text) -> str:
    """Cleans non-ascii characters from unicode string.

    Example
    -------
    \x88This text contains non-ascii characters!\x88
        -> This text contains non-ascii characters!
    """
    en = text.encode("ascii", "ignore")
    return en.decode()


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


def clean_ordered_bullets(text) -> str:
    """Cleans the start of bulleted text sections up to three “sub-section”
    bullets accounting numeric and alphanumeric types.

    Example
    -------
    1.1 This is a very important point -> This is a very important point
    a.b This is a very important point -> This is a very important point
    """
    text_sp = text.split()
    text_cl = " ".join(text_sp[1:])
    if any(["." not in text_sp[0], ".." in text_sp[0]]):
        return text

    bullet = re.split(pattern=r"[\.]", string=text_sp[0])
    if not bullet[-1]:
        del bullet[-1]

    if len(bullet[0]) > 2:
        return text

    return text_cl


def group_broken_paragraphs(
    text: str,
    line_split: re.Pattern = PARAGRAPH_PATTERN_RE,
    paragraph_split: re.Pattern = DOUBLE_PARAGRAPH_PATTERN_RE,
) -> str:
    """Groups paragraphs that have line breaks for visual/formatting purposes.
    For example:

    '''The big red fox
    is walking down the lane.

    At the end of the lane
    the fox met a bear.'''

    Gets converted to

    '''The big red fox is walking down the lane.
    At the end of the land the fox met a bear.'''
    """
    paragraphs = paragraph_split.split(text)
    clean_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue

        # NOTE(robinson) - This block is to account for lines like the following that shouldn't be
        # grouped together, but aren't separated by a double line break.
        #     Apache License
        #     Version 2.0, January 2004
        #     http://www.apache.org/licenses/
        para_split = line_split.split(paragraph)
        all_lines_short = all(len(line.strip().split(" ")) < 5 for line in para_split)

        if UNICODE_BULLETS_RE.match(paragraph.strip()):
            clean_paragraphs.extend(re.split(PARAGRAPH_PATTERN, paragraph))
        elif all_lines_short:
            clean_paragraphs.extend([line for line in para_split if line.strip()])
        else:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", paragraph))

    return "\n\n".join(clean_paragraphs)


# TODO(robinson) - There's likely a cleaner was to accomplish this and get all of the
# unicode characters instead of just the quotes. Doing this for now since quotes are
# an issue that are popping up in the SEC filings tests
def replace_unicode_quotes(text) -> str:
    """Replaces unicode bullets in text with the expected character

    Example
    -------
    \x93What a lovely quote!\x94 -> “What a lovely quote!”
    """
    # NOTE(robinson) - We should probably make this something more sane like a regex
    # instead of a whole big series of replaces
    text = text.replace("\x91", "‘")
    text = text.replace("\x92", "’")
    text = text.replace("\x93", "“")
    text = text.replace("\x94", "”")
    text = text.replace("&apos;", "'")
    text = text.replace("â\x80\x99", "'")
    text = text.replace("â\x80“", "—")
    text = text.replace("â\x80”", "–")
    text = text.replace("â\x80˜", "‘")
    text = text.replace("â\x80¦", "…")
    text = text.replace("â\x80™", "’")
    text = text.replace("â\x80œ", "“")
    text = text.replace("â\x80?", "”")
    text = text.replace("â\x80ť", "”")
    text = text.replace("â\x80ś", "“")
    text = text.replace("â\x80¨", "—")
    text = text.replace("â\x80ł", "″")
    text = text.replace("â\x80Ž", "")
    text = text.replace("â\x80‚", "")
    text = text.replace("â\x80‰", "")
    text = text.replace("â\x80‹", "")
    text = text.replace("â\x80", "")
    text = text.replace("â\x80s'", "")
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


def replace_mime_encodings(text: str, encoding: str = "utf-8") -> str:
    """Replaces MIME encodings with their equivalent characters in the specified encoding.

    Example
    -------
    5 w=E2=80-99s -> 5 w’s
    """
    formatted_encoding = format_encoding_str(encoding)
    return quopri.decodestring(text.encode(formatted_encoding)).decode(formatted_encoding)


def clean_prefix(text: str, pattern: str, ignore_case: bool = False, strip: bool = True) -> str:
    """Removes prefixes from a string according to the specified pattern. Strips leading
    whitespace if the strip parameter is set to True.

    Input
    -----
    text: The text to clean
    pattern: The pattern for the prefix. Can be a simple string or a regex pattern
    ignore_case: If True, ignores case in the pattern
    strip: If True, removes leading whitespace from the cleaned string.
    """
    flags = re.IGNORECASE if ignore_case else 0
    clean_text = re.sub(rf"^{pattern}", "", text, flags=flags)
    clean_text = clean_text.lstrip() if strip else clean_text
    return clean_text


def clean_postfix(text: str, pattern: str, ignore_case: bool = False, strip: bool = True) -> str:
    """Removes postfixes from a string according to the specified pattern. Strips trailing
    whitespace if the strip parameters is set to True.

    Input
    -----
    text: The text to clean
    pattern: The pattern for the postfix. Can be a simple string or a regex pattern
    ignore_case: If True, ignores case in the pattern
    strip: If True, removes trailing whitespace from the cleaned string.
    """
    flags = re.IGNORECASE if ignore_case else 0
    clean_text = re.sub(rf"{pattern}$", "", text, flags=flags)
    clean_text = clean_text.rstrip() if strip else clean_text
    return clean_text


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
    -----
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


def bytes_string_to_string(text: str, encoding: str = "utf-8"):
    """Converts a string representation of a byte string to a regular string using the
    specified encoding."""
    text_bytes = bytes([ord(char) for char in text])
    formatted_encoding = format_encoding_str(encoding)
    return text_bytes.decode(formatted_encoding)
