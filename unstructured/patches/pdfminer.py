from typing import Union

from pdfminer.psparser import END_KEYWORD, KWD, PSBaseParser, PSKeyword


def parse_keyword(self: PSBaseParser, s: bytes, i: int) -> int:
    """Patch for pdfminer method _parse_keyword of PSBaseParser. Changes are identical to the PR
    https://github.com/pdfminer/pdfminer.six/pull/885."""
    m = END_KEYWORD.search(s, i)
    if not m:
        j = len(s)
        self._curtoken += s[i:]
    else:
        j = m.start(0)
        self._curtoken += s[i:j]
    if self._curtoken == b"true":
        token: Union[bool, PSKeyword] = True
    elif self._curtoken == b"false":
        token = False
    else:
        token = KWD(self._curtoken)
    self._add_token(token)
    self._parse1 = self._parse_main
    return j
