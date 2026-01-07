from __future__ import annotations

import quopri
import re
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
    paragraph_pattern_re = re.compile(PARAGRAPH_PATTERN)

    # pytesseract converts some bullet points to standalone "e" characters.
    # Substitute "e" with bullets since they are later used in partition_text
    # to determine list element type.
    paragraph = E_BULLET_PATTERN.sub("·", paragraph).strip()

    bullet_paras = UNICODE_BULLETS_RE_0W.split(paragraph)
    clean_paragraphs = []
    for bullet in bullet_paras:
        if bullet:
            clean_paragraphs.append(paragraph_pattern_re.sub(" ", bullet))
    return clean_paragraphs


def group_broken_paragraphs(
    text: str,
    line_split: re.Pattern[str] = PARAGRAPH_PATTERN_RE,
    paragraph_split: re.Pattern[str] = DOUBLE_PARAGRAPH_PATTERN_RE,
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
    paragraph_pattern_re = (
        PARAGRAPH_PATTERN
        if isinstance(PARAGRAPH_PATTERN, re.Pattern)
        else re.compile(PARAGRAPH_PATTERN)
    )

    paragraphs = paragraph_split.split(text)
    clean_paragraphs = []
    for paragraph in paragraphs:
        stripped_par = paragraph.strip()
        if not stripped_par:
            continue

        if UNICODE_BULLETS_RE.match(stripped_par) or E_BULLET_PATTERN.match(stripped_par):
            clean_paragraphs.extend(group_bullet_paragraph(paragraph))
            continue
        # NOTE(robinson) - This block is to account for lines like the following that shouldn't be
        # grouped together, but aren't separated by a double line break.
        #     Apache License
        #     Version 2.0, January 2004
        #     http://www.apache.org/licenses/
        para_split = line_split.split(paragraph)
        all_lines_short = all(len(line.strip().split(" ")) < 5 for line in para_split)
        if all_lines_short:
            clean_paragraphs.extend(line for line in para_split if line.strip())
        else:
            clean_paragraphs.append(paragraph_pattern_re.sub(" ", paragraph))

    return "\n\n".join(clean_paragraphs)


def new_line_grouper(
    text: str,
    paragraph_split: re.Pattern[str] = LINE_BREAK_RE,
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
    line_split: re.Pattern[str] = LINE_BREAK_RE,
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
def replace_unicode_quotes(text: str) -> str:
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


# fmt: off
punkt = [33, 34, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 58, 59, 63, 64, 91, 92, 93, 95, 123,
         125, 161, 167, 171, 182, 183, 187, 191, 894, 903, 1370, 1371, 1372, 1373, 1374, 1375,
         1417, 1418, 1470, 1472, 1475, 1478, 1523, 1524, 1545, 1546, 1548, 1549, 1563, 1566, 1567,
         1642, 1643, 1644, 1645, 1748, 1792, 1793, 1794, 1795, 1796, 1797, 1798, 1799, 1800, 1801,
         1802, 1803, 1804, 1805, 2039, 2040, 2041, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103,
         2104, 2105, 2106, 2107, 2108, 2109, 2110, 2142, 2404, 2405, 2416, 2557, 2678, 2800, 3191,
         3204, 3572, 3663, 3674, 3675, 3844, 3845, 3846, 3847, 3848, 3849, 3850, 3851, 3852, 3853,
         3854, 3855, 3856, 3857, 3858, 3860, 3898, 3899, 3900, 3901, 3973, 4048, 4049, 4050, 4051,
         4052, 4057, 4058, 4170, 4171, 4172, 4173, 4174, 4175, 4347, 4960, 4961, 4962, 4963, 4964,
         4965, 4966, 4967, 4968, 5120, 5742, 5787, 5788, 5867, 5868, 5869, 5941, 5942, 6100, 6101,
         6102, 6104, 6105, 6106, 6144, 6145, 6146, 6147, 6148, 6149, 6150, 6151, 6152, 6153, 6154,
         6468, 6469, 6686, 6687, 6816, 6817, 6818, 6819, 6820, 6821, 6822, 6824, 6825, 6826, 6827,
         6828, 6829, 7002, 7003, 7004, 7005, 7006, 7007, 7008, 7164, 7165, 7166, 7167, 7227, 7228,
         7229, 7230, 7231, 7294, 7295, 7360, 7361, 7362, 7363, 7364, 7365, 7366, 7367, 7379, 8208,
         8209, 8210, 8211, 8212, 8213, 8214, 8215, 8216, 8217, 8218, 8219, 8220, 8221, 8222, 8223,
         8224, 8225, 8226, 8227, 8228, 8229, 8230, 8231, 8240, 8241, 8242, 8243, 8244, 8245, 8246,
         8247, 8248, 8249, 8250, 8251, 8252, 8253, 8254, 8255, 8256, 8257, 8258, 8259, 8261, 8262,
         8263, 8264, 8265, 8266, 8267, 8268, 8269, 8270, 8271, 8272, 8273, 8275, 8276, 8277, 8278,
         8279, 8280, 8281, 8282, 8283, 8284, 8285, 8286, 8317, 8318, 8333, 8334, 8968, 8969, 8970,
         8971, 9001, 9002, 10088, 10089, 10090, 10091, 10092, 10093, 10094, 10095, 10096, 10097,
         10098, 10099, 10100, 10101, 10181, 10182, 10214, 10215, 10216, 10217, 10218, 10219,
         10220, 10221, 10222, 10223, 10627, 10628, 10629, 10630, 10631, 10632, 10633, 10634,
         10635, 10636, 10637, 10638, 10639, 10640, 10641, 10642, 10643, 10644, 10645, 10646,
         10647, 10648, 10712, 10713, 10714, 10715, 10748, 10749, 11513, 11514, 11515, 11516,
         11518, 11519, 11632, 11776, 11777, 11778, 11779, 11780, 11781, 11782, 11783, 11784,
         11785, 11786, 11787, 11788, 11789, 11790, 11791, 11792, 11793, 11794, 11795, 11796,
         11797, 11798, 11799, 11800, 11801, 11802, 11803, 11804, 11805, 11806, 11807, 11808,
         11809, 11810, 11811, 11812, 11813, 11814, 11815, 11816, 11817, 11818, 11819, 11820,
         11821, 11822, 11824, 11825, 11826, 11827, 11828, 11829, 11830, 11831, 11832, 11833,
         11834, 11835, 11836, 11837, 11838, 11839, 11840, 11841, 11842, 11843, 11844, 11845,
         11846, 11847, 11848, 11849, 11850, 11851, 11852, 11853, 11854, 11855, 11858, 12289,
         12290, 12291, 12296, 12297, 12298, 12299, 12300, 12301, 12302, 12303, 12304, 12305,
         12308, 12309, 12310, 12311, 12312, 12313, 12314, 12315, 12316, 12317, 12318, 12319,
         12336, 12349, 12448, 12539, 42238, 42239, 42509, 42510, 42511, 42611, 42622, 42738,
         42739, 42740, 42741, 42742, 42743, 43124, 43125, 43126, 43127, 43214, 43215, 43256,
         43257, 43258, 43260, 43310, 43311, 43359, 43457, 43458, 43459, 43460, 43461, 43462,
         43463, 43464, 43465, 43466, 43467, 43468, 43469, 43486, 43487, 43612, 43613, 43614,
         43615, 43742, 43743, 43760, 43761, 44011, 64830, 64831, 65040, 65041, 65042, 65043,
         65044, 65045, 65046, 65047, 65048, 65049, 65072, 65073, 65074, 65075, 65076, 65077,
         65078, 65079, 65080, 65081, 65082, 65083, 65084, 65085, 65086, 65087, 65088, 65089,
         65090, 65091, 65092, 65093, 65094, 65095, 65096, 65097, 65098, 65099, 65100, 65101,
         65102, 65103, 65104, 65105, 65106, 65108, 65109, 65110, 65111, 65112, 65113, 65114,
         65115, 65116, 65117, 65118, 65119, 65120, 65121, 65123, 65128, 65130, 65131, 65281,
         65282, 65283, 65285, 65286, 65287, 65288, 65289, 65290, 65292, 65293, 65294, 65295,
         65306, 65307, 65311, 65312, 65339, 65340, 65341, 65343, 65371, 65373, 65375, 65376,
         65377, 65378, 65379, 65380, 65381, 65792, 65793, 65794, 66463, 66512, 66927, 67671,
         67871, 67903, 68176, 68177, 68178, 68179, 68180, 68181, 68182, 68183, 68184, 68223,
         68336, 68337, 68338, 68339, 68340, 68341, 68342, 68409, 68410, 68411, 68412, 68413,
         68414, 68415, 68505, 68506, 68507, 68508, 69293, 69461, 69462, 69463, 69464, 69465,
         69703, 69704, 69705, 69706, 69707, 69708, 69709, 69819, 69820, 69822, 69823, 69824,
         69825, 69952, 69953, 69954, 69955, 70004, 70005, 70085, 70086, 70087, 70088, 70093,
         70107, 70109, 70110, 70111, 70200, 70201, 70202, 70203, 70204, 70205, 70313, 70731,
         70732, 70733, 70734, 70735, 70746, 70747, 70749, 70854, 71105, 71106, 71107, 71108,
         71109, 71110, 71111, 71112, 71113, 71114, 71115, 71116, 71117, 71118, 71119, 71120,
         71121, 71122, 71123, 71124, 71125, 71126, 71127, 71233, 71234, 71235, 71264, 71265,
         71266, 71267, 71268, 71269, 71270, 71271, 71272, 71273, 71274, 71275, 71276, 71484,
         71485, 71486, 71739, 72004, 72005, 72006, 72162, 72255, 72256, 72257, 72258, 72259,
         72260, 72261, 72262, 72346, 72347, 72348, 72350, 72351, 72352, 72353, 72354, 72769,
         72770, 72771, 72772, 72773, 72816, 72817, 73463, 73464, 73727, 74864, 74865, 74866,
         74867, 74868, 92782, 92783, 92917, 92983, 92984, 92985, 92986, 92987, 92996, 93847,
         93848, 93849, 93850, 94178, 113823, 121479, 121480, 121481, 121482, 121483, 125278,
         125279]
# fmt: on
tbl = dict.fromkeys(punkt)


def remove_punctuation(s: str) -> str:
    """Removes punctuation from a given string."""
    return s.translate(tbl)


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
