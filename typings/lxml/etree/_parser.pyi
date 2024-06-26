from __future__ import annotations

from ._classlookup import ElementClassLookup

class HTMLParser:
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

class XMLParser:
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
