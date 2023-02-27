import sys
from typing import List

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

import re

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
    "\u204C",
    "\u204D",
    "\u2219",
    "\u25CB",
    "\u25CF",
    "\u25D8",
    "\u25E6",
    "\u2619",
    "\u2765",
    "\u2767",
    "\u29BE",
    "\u29BF",
    "\u002D",
    "",
    "\*",  # noqa: W605 NOTE(robinson) - skipping qa because we need the escape for the regex
    "\x95",
    "·",
]
UNICODE_BULLETS_RE = re.compile(f"(?:{'|'.join(UNICODE_BULLETS)})")

ENUMERATED_BULLETS_RE = re.compile(r"(?:(?:\d{1,3}|[a-z][A-Z])\.?){1,3}")

EMAIL_HEAD_PATTERN = (
    r"(MIME-Version: 1.0(.*)?\n)?Date:.*\nMessage-ID:.*\nSubject:.*\nFrom:.*\nTo:.*"
)
EMAIL_HEAD_RE = re.compile(EMAIL_HEAD_PATTERN)

# Helps split text by paragraphs
PARAGRAPH_PATTERN = "\n\n\n|\n\n|\r\n|\r|\n"  # noqa: W605 NOTE(harrell)

# IP Address examples: ba23::58b5:2236:45g2:88h2 or 10.0.2.01
IP_ADDRESS_PATTERN = (
    "[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}",  # noqa: W605 NOTE(harrell)
    # - skipping qa because we need the escape for the regex
    "[a-z0-9]{4}::[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}%?[0-9]*",
)
IP_ADDRESS_PATTERN_RE = re.compile(f"({'|'.join(IP_ADDRESS_PATTERN)})")

IP_ADDRESS_NAME_PATTERN = "[a-zA-Z0-9-]*\.[a-zA-Z]*\.[a-zA-Z]*"  # noqa: W605 NOTE(harrell)
# - skipping qa because we need the escape for the regex

# Mapi ID example: 32.88.5467.123
MAPI_ID_PATTERN = "[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*;"  # noqa: W605 NOTE(harrell)
# - skipping qa because we need the escape for the regex

# Date, time, timezone example: Fri, 26 Mar 2021 11:04:09 +1200
EMAIL_DATETIMETZ_PATTERN = "[a-zA-z]{3},\s[0-9]{2}\s[a-zA-Z]{3}\s[0-9]{4}\s[0-9]{2}:[0-9]{2}:[0-9]{2}\s[+0-9]{5}"  # noqa: W605,E501
# NOTE(harrell) - skipping qa because we need the escape for the regex

EMAIL_ADDRESS_PATTERN = "[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"  # noqa: W605 NOTE(harrell)
# - skipping qa because we need the escape for the regex
