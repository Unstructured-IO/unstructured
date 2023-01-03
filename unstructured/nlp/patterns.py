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
