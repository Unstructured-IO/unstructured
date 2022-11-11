from typing import List
import sys

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

import re

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
    "",
    "\*",  # noqa: W605 NOTE(robinson) - skipping qa because we need the escape for the regex
    "\x95",
    "·",
]
UNICODE_BULLETS_RE = re.compile(f"({'|'.join(UNICODE_BULLETS)})")
