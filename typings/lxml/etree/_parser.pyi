# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Generic

from .._types import _ET_co
from ._classlookup import ElementClassLookup

# Includes most stuff in _BaseParser
class _FeedParser(Generic[_ET_co]): ...

class HTMLParser(_FeedParser[_ET_co]):
    def __init__(
        self,
        *,
        encoding: str | None = None,
        remove_blank_text: bool = False,
        remove_comments: bool = False,
        remove_pis: bool = False,
        strip_cdata: bool = True,
        no_network: bool = True,
        recover: bool = True,
        compact: bool = True,
        default_doctype: bool = True,
        collect_ids: bool = True,
        huge_tree: bool = False,
    ) -> None: ...
    def set_element_class_lookup(self, lookup: ElementClassLookup | None = None) -> None: ...

class XMLParser(_FeedParser[_ET_co]):
    def __init__(
        self,
        *,
        encoding: str | None = None,
        attribute_defaults: bool = False,
        dtd_validation: bool = False,
        load_dtd: bool = False,
        no_network: bool = True,
        ns_clean: bool = False,
        recover: bool = False,
        huge_tree: bool = False,
        remove_blank_text: bool = False,
        remove_comments: bool = False,
        remove_pis: bool = False,
        strip_cdata: bool = True,
        collect_ids: bool = True,
        compact: bool = True,
    ) -> None: ...
