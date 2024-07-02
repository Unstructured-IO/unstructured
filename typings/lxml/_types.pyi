# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Any, Callable, Collection, Protocol, TypeVar

from typing_extensions import TypeAlias

from .etree import QName, _Element, _ElementTree

_ET = TypeVar("_ET", bound=_Element, default=_Element)
_ET_co = TypeVar("_ET_co", bound=_Element, default=_Element, covariant=True)
_KT_co = TypeVar("_KT_co", covariant=True)
_VT_co = TypeVar("_VT_co", covariant=True)

_AttrName: TypeAlias = str

_ElemPathArg: TypeAlias = str | QName

_ElementOrTree: TypeAlias = _ET | _ElementTree[_ET]

_TagName: TypeAlias = str

_TagSelector: TypeAlias = _TagName | Callable[..., _Element]

_XPathObject = Any

class SupportsLaxedItems(Protocol[_KT_co, _VT_co]):
    def items(self) -> Collection[tuple[_KT_co, _VT_co]]: ...
