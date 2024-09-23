# pyright: reportPrivateUsage=false

import sys
from typing import Iterable, Iterator, Literal

from _typeshed import SupportsRead, _T_co

from .._types import _FilePath, _TagSelector
from ._element import _Element

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

_NoNSEventNames: TypeAlias = Literal["start", "end", "comment", "pi"]

class iterparse(Iterator[_T_co]):
    """Incremental parser"""

    def __new__(
        cls,
        source: _FilePath | SupportsRead[bytes],
        events: Iterable[_NoNSEventNames],
        *,
        tag: _TagSelector | Iterable[_TagSelector] | None = None,
        attribute_defaults: bool = False,
        dtd_validation: bool = False,
        load_dtd: bool = False,
        no_network: bool = True,
        remove_blank_text: bool = False,
        compact: bool = True,
        resolve_entities: bool = True,
        remove_comments: bool = False,
        remove_pis: bool = False,
        strip_cdata: bool = True,
        encoding: str | None = None,
        html: bool = False,
        recover: bool | None = None,
        huge_tree: bool = False,
        collect_ids: bool = True,
    ) -> iterparse[tuple[_NoNSEventNames, _Element]]: ...
