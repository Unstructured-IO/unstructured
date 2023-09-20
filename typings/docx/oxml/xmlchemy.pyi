from typing import Any, Iterator

from lxml import etree

class BaseOxmlElement(etree.ElementBase):
    def __iter__(self) -> Iterator[BaseOxmlElement]: ...
    @property
    def xml(self) -> str: ...
    def xpath(self, xpath_str: str) -> Any:
        """Return type is typically Sequence[ElementBase], but ...

        lxml.etree.XPath has many possible return types including bool, (a "smart") str,
        float. The return type can also be a list containing ElementBase, comments,
        processing instructions, str, and tuple. So you need to cast the result based on
        the XPath expression you use.
        """
        ...
