import re
from typing import Final, List

# NOTE(robinson) - Modified from answers found on this stackoverflow post
# ref: https://stackoverflow.com/questions/16699007/
# regular-expression-to-match-standard-10-digit-phone-number
US_PHONE_NUMBERS_PATTERN = (
    r"(?:\+?(\d{1,3}))?[-. (]*(\d{3})?[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$"
)
US_PHONE_NUMBERS_RE = re.compile(US_PHONE_NUMBERS_PATTERN)

# NOTE(robinson) - Based on this regex from regex101. Regex was updated to run fast
# and avoid catastrophic backtracking
# ref: https://regex101.com/library/oR3jU1?page=673
US_CITY_STATE_ZIP_PATTERN = (
    r"(?i)\b(?:[A-Z][a-z.-]{1,15}[ ]?){1,5},\s?"
    r"(?:{Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida"
    r"|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland"
    r"|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|"
    r"New[ ]Hampshire|New[ ]Jersey|New[ ]Mexico|New[ ]York|North[ ]Carolina|North[ ]Dakota"
    r"|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode[ ]Island|South[ ]Carolina|South[ ]Dakota"
    r"|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West[ ]Virginia|Wisconsin|Wyoming}"
    r"|{AL|AK|AS|AZ|AR|CA|CO|CT|DE|DC|FM|FL|GA|GU|HI|ID|IL|IN|IA|KS|KY|LA|ME|MH|MD|MA|MI|MN"
    r"|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|MP|OH|OK|OR|PW|PA|PR|RI|SC|SD|TN|TX|UT|VT|VI|VA|"
    r"WA|WV|WI|WY})(, |\s)?(?:\b\d{5}(?:-\d{4})?\b)"
)
US_CITY_STATE_ZIP_RE = re.compile(US_CITY_STATE_ZIP_PATTERN)

UNICODE_BULLETS: Final[List[str]] = [
    "\u0095",
    "\u2022",
    "\u2023",
    "\u2043",
    "\u3164",
    "\u204c",
    "\u204d",
    "\u2219",
    "\u25cb",
    "\u25cf",
    "\u25d8",
    "\u25e6",
    "\u2619",
    "\u2765",
    "\u2767",
    "\u29be",
    "\u29bf",
    "\u002d",
    "\u2013",
    "",
    r"\*",
    "\x95",
    "·",
]
BULLETS_PATTERN = "|".join(UNICODE_BULLETS)

# NOTE - `-` (U+002D) and `–` (U+2013) are bullet glyphs *and* ordinary punctuation: an
# intra-word hyphen, an intra-number separator, or a minus sign. Two conditions have to
# hold before one of them may be read as a bullet, or ordinary text loses characters:
#
#   1. It must be at the start of a line. Used as an UNANCHORED delimiter, every
#      hyphenated value is shredded ("090-1234-5678" -> three paragraphs).
#   2. It must be followed by whitespace (or end there). A bullet is separated from the
#      item it introduces; a sign is not. Without this, "-123.45" reads as a bullet and
#      is silently rewritten to "123.45", flipping the value. Compare E_BULLET_PATTERN
#      below, which already requires `(?=\s)` for the same reason.
#
# They stay in UNICODE_BULLETS so `clean_bullets`, `is_bulleted_text` and
# `_is_empty_bullet` still recognise a leading "- item", via the qualified alternation in
# UNICODE_BULLETS_RE.
AMBIGUOUS_BULLETS: Final[List[str]] = ["-", "\u2013"]
UNAMBIGUOUS_BULLETS_PATTERN = "|".join(b for b in UNICODE_BULLETS if b not in AMBIGUOUS_BULLETS)
AMBIGUOUS_BULLETS_PATTERN = "|".join(AMBIGUOUS_BULLETS)
# An ambiguous glyph is a bullet only when whitespace (or the end of the text) follows it.
QUALIFIED_AMBIGUOUS_BULLET = f"(?:{AMBIGUOUS_BULLETS_PATTERN})(?=\\s|$)"
# Any whitespace except a newline or carriage return. Indentation may be a tab, a NO-BREAK
# SPACE or an EM SPACE in extracted text, so the class has to be wider than " \t".
#
# It deliberately still admits FORM FEED, VERTICAL TAB, NEL, LINE SEPARATOR and friends.
# Those sit BETWEEN the newline and the bullet, so a class that refused them would leave
# the `(?<=\n)` lookbehind unable to reach the dash, and "- a\n\x0c- b" would collapse into
# a single item instead of two. They are consumed rather than preserved, which matches the
# previous behaviour: the paragraph is rejoined with `PARAGRAPH_PATTERN` (`\s*\n\s*`)
# substituted for a space, so this whitespace was normalised away regardless.
NON_NEWLINE_WHITESPACE = r"[^\S\n\r]*"
# The ambiguous branch is anchored to the start of a line so this regex stays safe under
# `.split()` as well as `.match()`: unanchored, it splits "Amount - forty" mid-line.
# Indentation is deliberately NOT consumed here -- that would make `.match()` strip a
# leading "  - item" while leaving "  \u25cf item" alone, an asymmetry between glyph
# classes. BULLET_SPLIT_RE_0W below handles indentation for the splitting path.
UNICODE_BULLETS_RE = re.compile(
    f"(?:(?:{UNAMBIGUOUS_BULLETS_PATTERN})|(?:(?:(?<=\\n)|\\A){QUALIFIED_AMBIGUOUS_BULLET}))"
    f"(?!{BULLETS_PATTERN})",
)
# zero-width positive lookahead so bullet characters will not be removed when using
# .split(). Retained for backwards compatibility; prefer BULLET_SPLIT_RE_0W, which does
# not split hyphenated values.
UNICODE_BULLETS_RE_0W = re.compile(f"(?={BULLETS_PATTERN})(?<!{BULLETS_PATTERN})")
# Same zero-width split, but an ambiguous bullet counts only at the start of a line and
# only when whitespace follows it, so a hyphen or a minus sign is left alone.
BULLET_SPLIT_RE_0W = re.compile(
    f"(?:(?={UNAMBIGUOUS_BULLETS_PATTERN})(?<!{UNAMBIGUOUS_BULLETS_PATTERN}))"
    f"|(?:(?:(?<=\\n)|\\A){NON_NEWLINE_WHITESPACE}(?={QUALIFIED_AMBIGUOUS_BULLET}))",
)
E_BULLET_PATTERN = re.compile(r"^e(?=\s)", re.MULTILINE)

# NOTE(klaijan) - Captures reference of format [1] or [i] or [a] at any point in the line.
REFERENCE_PATTERN = r"\[(?:[\d]+|[a-z]|[ivxlcdm])\]"
REFERENCE_PATTERN_RE = re.compile(REFERENCE_PATTERN)

ENUMERATED_BULLETS_RE = re.compile(r"(?:(?:\d{1,3}|[a-z][A-Z])\.?){1,3}")

EMAIL_HEAD_PATTERN = (
    r"(MIME-Version: 1.0(.*)?\n)?Date:.*\nMessage-ID:.*\nSubject:.*\nFrom:.*\nTo:.*"
)
EMAIL_HEAD_RE = re.compile(EMAIL_HEAD_PATTERN)

# Helps split text by paragraphs. There must be one newline, with potential whitespace
# (incluing \r and \n chars) on either side
PARAGRAPH_PATTERN = r"\s*\n\s*"

PARAGRAPH_PATTERN_RE = re.compile(
    f"((?:{UNAMBIGUOUS_BULLETS_PATTERN})|{PARAGRAPH_PATTERN})(?!{UNAMBIGUOUS_BULLETS_PATTERN}|$)",
)
DOUBLE_PARAGRAPH_PATTERN_RE = re.compile("(" + PARAGRAPH_PATTERN + "){2}")

# Captures all new line \n and keeps the \n as its own element,
# considers \n\n as two separate elements
LINE_BREAK = r"(?<=\n)"
LINE_BREAK_RE = re.compile(LINE_BREAK)

# NOTE(klaijan) - captures a line that does not ends with period (.)
ONE_LINE_BREAK_PARAGRAPH_PATTERN = r"^(?:(?!\.\s*$).)*$"
ONE_LINE_BREAK_PARAGRAPH_PATTERN_RE = re.compile(ONE_LINE_BREAK_PARAGRAPH_PATTERN)

# IP Address examples: ba23::58b5:2236:45g2:88h2, 10.0.2.01 or 68.183.71.12
IP_ADDRESS_PATTERN = (
    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}",
    "[a-z0-9]{4}::[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}%?[0-9]*",
)
IP_ADDRESS_PATTERN_RE = re.compile(f"({'|'.join(IP_ADDRESS_PATTERN)})")

IP_ADDRESS_NAME_PATTERN = r"[a-zA-Z0-9-]*\.[a-zA-Z]*\.[a-zA-Z]*"

# Mapi ID example: 32.88.5467.123
MAPI_ID_PATTERN = r"[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*;"

# Date, time, timezone example: Fri, 26 Mar 2021 11:04:09 +1200
EMAIL_DATETIMETZ_PATTERN = (
    r"[A-Za-z]{3},\s\d{1,2}\s[A-Za-z]{3}\s\d{4}\s\d{2}:\d{2}:\d{2}\s[+-]\d{4}"
)
EMAIL_DATETIMETZ_PATTERN_RE = re.compile(EMAIL_DATETIMETZ_PATTERN)

EMAIL_ADDRESS_PATTERN = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
EMAIL_ADDRESS_PATTERN_RE = re.compile(EMAIL_ADDRESS_PATTERN)

ENDS_IN_PUNCT_PATTERN = r"[^\w\s]\Z"
ENDS_IN_PUNCT_RE = re.compile(ENDS_IN_PUNCT_PATTERN)

# NOTE(robinson) - Used to detect if text is in the expected "list of dicts"
# format for document elements
LIST_OF_DICTS_PATTERN = r"\A\s*\[\s*{?"


# (?s) dot all (including newline characters)
# \{(?=.*:) opening brace and at least one colon
# .*? any characters (non-greedy)
# (?:\}|$) non-capturing group that matches either the closing brace } or the end of
# the string to handle cases where the JSON is cut off
# | or
# \[(?s:.*?)\] matches the opening bracket [ in a JSON array and any characters inside the array
# (?:$|,|\]) non-capturing group that matches either the end of the string, a comma,
# or the closing bracket to handle cases where the JSON array is cut off
JSON_PATTERN = r"(?s)\{(?=.*:).*?(?:\}|$)|\[(?s:.*?)\](?:$|,|\])"


# taken from https://stackoverflow.com/a/3845829/12406158
VALID_JSON_CHARACTERS = r"[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]"

IMAGE_URL_PATTERN = (
    r"(?i)https?://"
    r"(?:[a-z0-9$_@.&+!*\\(\\),%-])+"
    r"(?:/[a-z0-9$_@.&+!*\\(\\),%-]*)*"
    r"\.(?:jpg|jpeg|png|gif|bmp|heic)"
)

# NOTE(klaijan) - only supports one level numbered list for now
# e.g. 1. 2. 3. or 1) 2) 3), not 1.1 1.2 1.3
NUMBERED_LIST_PATTERN = r"^\d+(\.|\))\s(.+)"
NUMBERED_LIST_RE = re.compile(NUMBERED_LIST_PATTERN)
