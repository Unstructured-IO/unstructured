# pyright: reportPrivateUsage=false

from __future__ import annotations

from ._element import _Element

class ElementBase(_Element):
    """The public Element class

    Original Docstring
    ------------------
    All custom Element classes must inherit from this one.
    To create an Element, use the `Element()` factory.

    BIG FAT WARNING: Subclasses *must not* override `__init__` or
    `__new__` as it is absolutely undefined when these objects will be
    created or destroyed.  All persistent state of Elements must be
    stored in the underlying XML.  If you really need to initialize
    the object after creation, you can implement an ``_init(self)``
    method that will be called directly after object creation.

    Subclasses of this class can be instantiated to create a new
    Element.  By default, the tag name will be the class name and the
    namespace will be empty.  You can modify this with the following
    class attributes:

    * TAG - the tag name, possibly containing a namespace in Clark
      notation

    * NAMESPACE - the default namespace URI, unless provided as part
      of the TAG attribute.

    * HTML - flag if the class is an HTML tag, as opposed to an XML
      tag.  This only applies to un-namespaced tags and defaults to
      false (i.e. XML).

    * PARSER - the parser that provides the configuration for the
      newly created document.  Providing an HTML parser here will
      default to creating an HTML element.

    In user code, the latter three are commonly inherited in class
    hierarchies that implement a common namespace.
    """

    def __init__(
        self,
        *children: object,
        attrib: dict[str, str] | None = None,
        **_extra: str,
    ) -> None: ...
    def _init(self) -> None: ...

class ElementClassLookup:
    """Superclass of Element class lookups"""

class ElementDefaultClassLookup(ElementClassLookup):
    """Element class lookup scheme that always returns the default Element
    class.

    The keyword arguments ``element``, ``comment``, ``pi`` and ``entity``
    accept the respective Element classes."""

    def __init__(
        self,
        element: type[ElementBase] | None = None,
    ) -> None: ...

class FallbackElementClassLookup(ElementClassLookup):
    """Superclass of Element class lookups with additional fallback"""

    @property
    def fallback(self) -> ElementClassLookup | None: ...
    def __init__(self, fallback: ElementClassLookup | None = None) -> None: ...
    def set_fallback(self, lookup: ElementClassLookup) -> None:
        """Sets the fallback scheme for this lookup method"""
