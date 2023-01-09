from typing import List
import sys

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
UNICODE_BULLETS_RE = re.compile(f"({'|'.join(UNICODE_BULLETS)})")

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
