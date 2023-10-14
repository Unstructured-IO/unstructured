import quopri
import re
import sys
import unicodedata
from typing import Optional, Tuple

import numpy as np

from unstructured.file_utils.encoding import (
    format_encoding_str,
)
from unstructured.nlp.patterns import (
    DOUBLE_PARAGRAPH_PATTERN_RE,
    E_BULLET_PATTERN,
    LINE_BREAK_RE,
    PARAGRAPH_PATTERN,
    PARAGRAPH_PATTERN_RE,
    UNICODE_BULLETS_RE,
    UNICODE_BULLETS_RE_0W,
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


def clean_bullets(text: str) -> str:
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


def clean_ligatures(text) -> str:
    """Replaces ligatures with their most likely equivalent characters.

    Example
    -------
    The beneﬁts -> The benefits
    High quality ﬁnancial -> High quality financial
    """
    ligatures_map = {
        "æ": "ae",
        "Æ": "AE",
        "ﬀ": "ff",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ʪ": "ls",
        "œ": "oe",
        "Œ": "OE",
        "ȹ": "qp",
        "ﬆ": "st",
        "ʦ": "ts",
    }
    cleaned_text: str = text
    for k, v in ligatures_map.items():
        cleaned_text = cleaned_text.replace(k, v)

    return cleaned_text


def group_bullet_paragraph(paragraph: str) -> list:
    """Groups paragraphs with bullets that have line breaks for visual/formatting purposes.
    For example:

    '''○ The big red fox
    is walking down the lane.

    ○ At the end of the lane
    the fox met a friendly bear.'''

    Gets converted to

    '''○ The big red fox is walking down the lane.
    ○ At the end of the land the fox met a bear.'''
    """
    clean_paragraphs = []
    # pytesseract converts some bullet points to standalone "e" characters.
    # Substitute "e" with bullets since they are later used in partition_text
    # to determine list element type.
    paragraph = (re.sub(E_BULLET_PATTERN, "·", paragraph)).strip()

    bullet_paras = re.split(UNICODE_BULLETS_RE_0W, paragraph)
    for bullet in bullet_paras:
        if bullet:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", bullet))
    return clean_paragraphs


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
        # pytesseract converts some bullet points to standalone "e" characters
        if UNICODE_BULLETS_RE.match(paragraph.strip()) or E_BULLET_PATTERN.match(paragraph.strip()):
            clean_paragraphs.extend(group_bullet_paragraph(paragraph))
        elif all_lines_short:
            clean_paragraphs.extend([line for line in para_split if line.strip()])
        else:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", paragraph))

    return "\n\n".join(clean_paragraphs)


def new_line_grouper(
    text: str,
    paragraph_split: re.Pattern = LINE_BREAK_RE,
) -> str:
    """
    Concatenates text document that has one-line paragraph break pattern

    For example,

    Iwan Roberts
    Roberts celebrating after scoring a goal for Norwich City
    in 2004

    Will be returned as:

    Iwan Roberts\n\nRoberts celebrating after scoring a goal for Norwich City\n\nin 2004
    """
    paragraphs = paragraph_split.split(text)
    clean_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        clean_paragraphs.append(paragraph)
    return "\n\n".join(clean_paragraphs)


def blank_line_grouper(
    text: str,
    paragraph_split: re.Pattern = DOUBLE_PARAGRAPH_PATTERN_RE,
) -> str:
    """
    Concatenates text document that has blank-line paragraph break pattern

    For example,

    Vestibulum auctor dapibus neque.

    Nunc dignissim risus id metus.

    Will be returned as:

    Vestibulum auctor dapibus neque.\n\nNunc dignissim risus id metus.\n\n

    """
    return group_broken_paragraphs(text)


def auto_paragraph_grouper(
    text: str,
    line_split: re.Pattern = LINE_BREAK_RE,
    max_line_count: int = 2000,
    threshold: float = 0.1,
) -> str:
    """
    Checks the ratio of new line (\n) over the total max_line_count

    If the ratio of new line is less than the threshold,
    the document is considered a new-line grouping type
    and return the original text

    If the ratio of new line is greater than or equal to the threshold,
    the document is considered a blank-line grouping type
    and passed on to blank_line_grouper function
    """
    lines = line_split.split(text)
    max_line_count = min(len(lines), max_line_count)
    line_count, empty_line_count = 0, 0
    for line in lines[:max_line_count]:
        line_count += 1
        if not line.strip():
            empty_line_count += 1
    ratio = empty_line_count / line_count

    # NOTE(klaijan) - for ratio < threshold, we pass to new-line grouper,
    # otherwise to blank-line grouper
    if ratio < threshold:
        return new_line_grouper(text)
    else:
        return blank_line_grouper(text)


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


def remove_sentence_punctuation(s: str, exclude_punctuation: Optional[list]) -> str:
    tbl_new = tbl.copy()
    if exclude_punctuation:
        for punct in exclude_punctuation:
            del tbl_new[ord(punct)]
    s = s.translate(tbl_new)
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


def clean_extra_whitespace_with_index_run(text: str) -> Tuple[str, np.ndarray]:
    """Cleans extra whitespace characters that appear between words.
    Calculate distance between characters of original text and cleaned text.

    Returns cleaned text along with array of indices it has moved from original.

    Example
    -------
    ITEM 1.     BUSINESS -> ITEM 1. BUSINESS
    array([0., 0., 0., 0., 0., 0., 0., 0., 4., 4., 4., 4., 4., 4., 4., 4., 4., 4., 4., 4.]))
    """

    cleaned_text = re.sub(r"[\xa0\n]", " ", text)
    cleaned_text = re.sub(r"([ ]{2,})", " ", cleaned_text)

    cleaned_text = cleaned_text.strip()

    moved_indices = np.zeros(len(text))

    distance, original_index, cleaned_index = 0, 0, 0
    while cleaned_index < len(cleaned_text):
        if text[original_index] == cleaned_text[cleaned_index] or (
            bool(re.match("[\xa0\n]", text[original_index]))
            and bool(re.match(" ", cleaned_text[cleaned_index]))
        ):
            moved_indices[cleaned_index] = distance
            original_index += 1
            cleaned_index += 1
            continue

        distance += 1
        moved_indices[cleaned_index] = distance
        original_index += 1

    moved_indices[cleaned_index:] = distance

    return cleaned_text, moved_indices


def index_adjustment_after_clean_extra_whitespace(index, moved_indices) -> int:
    return int(index - moved_indices[index])
