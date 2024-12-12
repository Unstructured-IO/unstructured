import functools
from typing import Tuple, Union

import pdfminer
from pdfminer.psparser import (
    END_KEYWORD,
    KWD,
    PSEOF,
    PSBaseParser,
    PSBaseParserToken,
    PSKeyword,
    log,
)

factory_seek = PSBaseParser.seek


@functools.wraps(PSBaseParser.seek)
def seek(self: PSBaseParser, pos: int) -> None:
    factory_seek(self, pos)
    self.eof = False


@functools.wraps(PSBaseParser._parse_keyword)
def _parse_keyword(self, s: bytes, i: int) -> int:
    m = END_KEYWORD.search(s, i)
    if m:
        j = m.start(0)
        self._curtoken += s[i:j]
    else:
        self._curtoken += s[i:]
        return len(s)
    if self._curtoken == b"true":
        token: Union[bool, PSKeyword] = True
    elif self._curtoken == b"false":
        token = False
    else:
        token = KWD(self._curtoken)
    self._add_token(token)
    self._parse1 = self._parse_main
    return j


@functools.wraps(PSBaseParser.nexttoken)
def nexttoken(self) -> Tuple[int, PSBaseParserToken]:
    if self.eof:
        # It's not really unexpected, come on now...
        raise PSEOF("Unexpected EOF")
    while not self._tokens:
        try:
            self.fillbuf()
            self.charpos = self._parse1(self.buf, self.charpos)
        except PSEOF:
            # If we hit EOF in the middle of a token, try to parse
            # it by tacking on whitespace, and delay raising PSEOF
            # until next time around
            self.charpos = self._parse1(b"\n", 0)
            self.eof = True
            # Oh, so there wasn't actually a token there? OK.
            if not self._tokens:
                raise
    token = self._tokens.pop(0)
    log.debug("nexttoken: %r", token)
    return token


def patch_psparser():
    """Monkey-patch certain versions of pdfminer.six to avoid dropping
    tokens at EOF (before 20231228) and splitting tokens at buffer
    boundaries (20231228 and 20240706).
    """
    # Presuming the bug will be fixed in the next release
    if pdfminer.__version__ <= "20240706":
        PSBaseParser.seek = seek
        PSBaseParser._parse_keyword = _parse_keyword
        PSBaseParser.nexttoken = nexttoken
