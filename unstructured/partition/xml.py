from __future__ import annotations

import codecs
import copy
from io import BytesIO
from typing import IO, Any, Iterator, cast

from lxml import etree

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, ElementMetadata, Text
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import (
    exactly_one,
    rewind_if_spooled,
)
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.text import element_from_text
from unstructured.telemetry import partition_runtime_telemetry

DETECTION_ORIGIN: str = "xml"


@partition_runtime_telemetry("xml")
@apply_metadata(FileType.XML)
@add_chunking_strategy
def partition_xml(
    filename: str | None = None,
    *,
    file: IO[bytes] | None = None,
    text: str | None = None,
    encoding: str | None = None,
    xml_keep_tags: bool = False,
    xml_path: str | None = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an XML document into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The text of the XML file.
    encoding
        The encoding used to decode `filename` or `file`. When None, the XML parser detects
        the encoding when extracting text; when retaining tags, text encoding detection is used.
        The Python `utf-8-sig` codec and its aliases are accepted for UTF-8 with or without a BOM.
        Does not affect an already-decoded `text` input.
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags.
    xml_path
        The xml_path to use for extracting the text. Only used if xml_keep_tags=False.
    """
    exactly_one(filename=filename, file=file, text=text)

    elements: list[Element] = []

    metadata = ElementMetadata(
        filename=filename, last_modified=get_last_modified_date(filename) if filename else None
    )
    metadata.detection_origin = DETECTION_ORIGIN

    if xml_keep_tags:
        if filename:
            raw_text = read_txt_file(filename=filename, encoding=encoding)[1]
        elif file:
            raw_text = read_txt_file(file=rewind_if_spooled(file), encoding=encoding)[1]
        else:
            assert text is not None
            raw_text = text

        elements = [Text(text=raw_text, metadata=metadata)]

    else:
        leaf_elements = get_leaf_elements(
            filename=filename,
            file=file,
            text=text,
            xml_path=xml_path,
            encoding=encoding,
        )
        for leaf_element in leaf_elements:
            if leaf_element:
                element = element_from_text(leaf_element)
                element.metadata = copy.deepcopy(metadata)
                elements.append(element)

    return elements


def get_leaf_elements(
    filename: str | None,
    file: IO[bytes] | None,
    text: str | None,
    xml_path: str | None,
    *,
    encoding: str | None = None,
) -> Iterator[str | None]:
    """Get leaf elements from the XML tree defined in filename, file, or text."""
    exactly_one(filename=filename, file=file, text=text)
    if filename:
        return _get_leaf_elements(filename, xml_path=xml_path, encoding=encoding)
    elif file:
        return _get_leaf_elements(
            file=rewind_if_spooled(file), xml_path=xml_path, encoding=encoding
        )
    else:
        b = BytesIO(bytes(cast(str, text), encoding="utf-8"))
        return _get_leaf_elements(b, xml_path=xml_path)


def _get_leaf_elements(
    file: str | IO[bytes],
    xml_path: str | None,
    *,
    encoding: str | None = None,
) -> Iterator[str | None]:
    """Parse the XML tree in a memory efficient manner if possible."""
    if encoding is not None:
        try:
            is_utf8_sig = codecs.lookup(encoding).name == "utf-8-sig"
        except LookupError:
            is_utf8_sig = False
        if is_utf8_sig:
            encoding = "UTF-8"

    events = ("start", "end", "comment", "pi")
    element_iterator = etree.iterparse(
        file, events=events, encoding=encoding, resolve_entities=False
    )
    # NOTE(alan) If xml_path is used for filtering, I've yet to find a good way to stream
    # elements through in a memory efficient way, so we bite the bullet and load it all into
    # memory.
    if xml_path is not None:
        # -- the root's start, after any comment or processing instruction ahead of it --
        element = next(node for event, node in element_iterator if event == "start")
        matches = [match for match in etree.XPath(xml_path)(element) if isinstance(match.tag, str)]
        selected = set(matches)
        for match in matches:
            # -- a match inside another match is already part of that one's text --
            if any(ancestor in selected for ancestor in match.iterancestors()):
                continue
            yield from _partition_events(etree.iterwalk(match, events=events), clear=False)
        return

    yield from _partition_events(element_iterator, clear=True)


# -- Pieces a run without text of its own holds, those of its inline children included, before
# -- they are emitted as blocks, so a long run of leaf elements, of blank elements nested at any
# -- depth, or of whitespace, is not kept until the document ends.
_MAX_PENDING_PIECES = 1000
# -- Characters of text such a run holds, its inline children's included, so a few long runs of
# -- whitespace below the piece limit are not kept until the document ends either.
_MAX_PENDING_CHARS = 1 << 20


class _Inline:
    """The pieces of an inline child element, and whether any of them is more than whitespace.

    `inner` is the text the element stands for on its own: its pieces, or for a wrapper around a
    single child, as `<paragraph> <content>...</content> </paragraph>`, that child's, without the
    wrapper's whitespace.
    """

    __slots__ = ("pieces", "nonblank", "inner")

    def __init__(self, pieces: list[str | _Inline], nonblank: bool, inner: list[str | _Inline]):
        self.pieces = pieces
        self.nonblank = nonblank
        self.inner = inner


class _Run:
    """The text of an element since its last structural child, kept as pieces until it is final.

    A piece is text of the element itself (its `.text` or a child's tail) or an inline child,
    whose pieces are referenced rather than copied, so nested inline elements are joined once.
    """

    __slots__ = ("pieces", "has_text", "items", "weight", "size")

    def __init__(self):
        self.pieces: list[str | _Inline] = []
        # -- text of the element itself that is more than whitespace --
        self.has_text = False
        # -- inline children with text that is more than whitespace --
        self.items = 0
        # -- the pieces held, counting those of inline children, which `pieces` only references --
        self.weight = 0
        # -- the characters of text held, counting those of inline children --
        self.size = 0

    @property
    def nonblank(self) -> bool:
        return self.has_text or self.items > 0

    def add_text(self, text: str | None) -> None:
        if text:
            self.pieces.append(text)
            self.weight += 1
            self.size += len(text)
            self.has_text = self.has_text or not text.isspace()

    def add_inline(self, child: _Run) -> None:
        inner = child.pieces
        if not child.has_text and child.items == 1:
            inner = next(p.inner for p in child.pieces if isinstance(p, _Inline) and p.nonblank)
        self.pieces.append(_Inline(child.pieces, child.nonblank, inner))
        self.weight += child.weight + 1
        self.size += child.size
        self.items += child.nonblank

    @property
    def over_budget(self) -> bool:
        """Whether the run holds too much to wait for text of its own, which would join it."""
        return not self.has_text and (
            self.weight >= _MAX_PENDING_PIECES or self.size >= _MAX_PENDING_CHARS
        )

    def blocks(self) -> Iterator[str]:
        """One text when the run has text of its own, as prose does, else one per inline child."""
        if self.has_text:
            yield _flatten(self.pieces)
            return
        for piece in self.pieces:
            if isinstance(piece, _Inline) and piece.nonblank:
                yield _flatten(piece.inner)


def _flatten(pieces: list[str | _Inline]) -> str:
    """The text of `pieces`, with the pieces of nested inline children, in document order."""
    texts: list[str] = []
    iterators = [iter(pieces)]
    while iterators:
        for piece in iterators[-1]:
            if isinstance(piece, str):
                texts.append(piece)
            else:
                iterators.append(iter(piece.pieces))
                break
        else:
            iterators.pop()
    return "".join(texts)


class _Frame:
    """An element that has started and not ended yet."""

    __slots__ = (
        "element",
        "clear",
        "run",
        "text_read",
        "tail_owner",
        "has_children",
        "structural",
    )

    def __init__(self, element: etree._Element, clear: bool):  # pyright: ignore[reportPrivateUsage]
        self.element = element
        # -- whether the tree may be changed, which the streaming route does to release text --
        self.clear = clear
        self.run = _Run()
        self.text_read = False
        # -- the last child node whose tail is not read yet --
        self.tail_owner: etree._Element | None = None  # pyright: ignore[reportPrivateUsage]
        self.has_children = False
        # -- whether the element has emitted texts already; its later runs are texts of its own --
        self.structural = False

    def catch_up(self) -> None:
        """Read the text that is complete by now: the element's own text before its first child,
        and the tail of its last child, once another child starts or the element ends."""
        if not self.text_read:
            self.run.add_text(self.element.text)
            self.text_read = True
        if self.tail_owner is not None:
            self.run.add_text(self.tail_owner.tail)
            if self.clear:
                # -- the run holds the tail now; the node, still attached, need not --
                self.tail_owner.tail = None
            self.tail_owner = None


def _partition_events(
    events: Iterator[tuple[str, Any]],
    clear: bool,
) -> Iterator[str]:
    """The texts of the XML tree that `events` walk, in document order, as soon as each is final.

    An element with text of its own, as in `<p>The <b>quick</b> brown fox.</p>`, is one text that
    runs through its inline children. A container of separate texts, such as a record of fields
    or a list of items, is structural: its children's texts stay apart, and so do the runs of text
    around it in its ancestors, as in `<body>Inventory:<record>...</record></body>`. Text is read
    only when the parser has finished it, at the end of an element or of a later sibling.
    """
    stack: list[_Frame] = []
    # -- the frames below this index have nothing pending: no run, text or tail. Whatever gives a
    # -- frame pending text lowers it to that frame, or a flush would skip the frame and emit its
    # -- text after texts that follow it --
    clean = 0

    def flush() -> Iterator[str]:
        """Emit what the open elements hold, outermost first, ahead of the texts that follow."""
        nonlocal clean
        for frame in stack[clean:]:
            frame.catch_up()
            if frame.run.pieces:
                yield from frame.run.blocks()
                frame.run = _Run()
            frame.structural = True
        clean = len(stack)

    for event, node in events:
        if event == "start":
            if stack:
                stack[-1].catch_up()
                stack[-1].has_children = True
                if stack[-1].run.over_budget:
                    yield from flush()
            stack.append(_Frame(node, clear))
        elif event in ("comment", "pi"):
            # -- a comment or processing instruction adds only its tail, to its parent's text --
            if stack and node.getparent() is stack[-1].element:
                stack[-1].catch_up()
                if stack[-1].run.over_budget:
                    yield from flush()
                stack[-1].tail_owner = node
                clean = min(clean, len(stack) - 1)
        elif event == "end":
            frame = stack.pop()
            clean = min(clean, max(len(stack) - 1, 0))
            frame.catch_up()
            run = frame.run
            if not frame.structural and frame.has_children and not run.has_text and run.items > 1:
                yield from flush()
                frame.structural = True
            if frame.structural or not stack:
                yield from run.blocks()
            else:
                parent = stack[-1]
                parent.run.add_inline(run)
                if parent.run.over_budget:
                    yield from flush()
            if stack:
                stack[-1].tail_owner = node
                clean = min(clean, len(stack) - 1)
            if clear:
                # -- the tail is text of the parent, read once the parent has it complete --
                node.clear(keep_tail=True)
