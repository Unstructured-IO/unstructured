"""PDF link offsets follow emitted text rather than the count of PDF glyph objects."""

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pdf_image.pdfminer_processing import process_data_with_pdfminer

LINK_URL = "https://example.com/linked-text"


def _pdf_with_transformed_prefix(
    *, fake_bold: bool, multiline: bool, glyph_text: str | None
) -> BytesIO:
    """Build a real PDF with ordinary links after duplicated or expanded glyphs."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=150)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    if glyph_text is not None:
        # A single glyph can have several Unicode code points in its ToUnicode map.
        # Explicit glyph widths avoid looking up the expanded Unicode string in
        # the standard font's single-character metrics.
        font[NameObject("/BaseFont")] = NameObject("/LinkPrefix")
        font[NameObject("/FirstChar")] = NumberObject(32)
        font[NameObject("/LastChar")] = NumberObject(90)
        widths = {32: 278, 65: 667, 73: 278, 75: 667, 76: 556, 78: 722}
        font[NameObject("/Widths")] = ArrayObject(
            [NumberObject(widths.get(code, 600)) for code in range(32, 91)]
        )
        font[NameObject("/FontDescriptor")] = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/FontDescriptor"),
                NameObject("/FontName"): NameObject("/LinkPrefix"),
                NameObject("/Flags"): NumberObject(32),
                NameObject("/FontBBox"): ArrayObject(
                    [NumberObject(v) for v in (-100, -207, 1000, 900)]
                ),
                NameObject("/Ascent"): NumberObject(718),
                NameObject("/Descent"): NumberObject(-207),
                NameObject("/CapHeight"): NumberObject(718),
                NameObject("/StemV"): NumberObject(88),
                NameObject("/ItalicAngle"): NumberObject(0),
            }
        )
        cmap = DecodedStreamObject()
        cmap.set_data(
            (
                "/CIDInit /ProcSet findresource begin 12 dict begin begincmap "
                "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def "
                "/CMapName /LinkPrefix def /CMapType 2 def "
                "1 begincodespacerange <00> <ff> endcodespacerange "
                f"1 beginbfchar <41> <{glyph_text.encode('utf-16-be').hex()}> endbfchar "
                "endcmap CMapName currentdict /CMap defineresource pop end end"
            ).encode("ascii")
        )
        font[NameObject("/ToUnicode")] = writer._add_object(cmap)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )

    prefix = (
        [("A", 8.004)]
        if glyph_text is not None
        else [("B", 8.004), ("O", 9.336), ("L", 6.672), ("D", 8.664)]
    )
    if not multiline:
        prefix.append((" ", 3.336))
    commands = []
    x, y = 20.0, 100.0
    for character, width in prefix:
        commands.append(f"BT /F1 12 Tf 1 0 0 1 {x} {y} Tm ({character}) Tj ET")
        if fake_bold:
            commands.append(f"BT /F1 12 Tf 1 0 0 1 {x + 0.1} {y} Tm ({character}) Tj ET")
        x += width
    if multiline:
        x, y = 20.0, 85.0
    commands.append(f"BT /F1 12 Tf 1 0 0 1 {x} {y} Tm (LINK) Tj ET")
    contents = DecodedStreamObject()
    contents.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(contents)
    annotation = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject(
                [FloatObject(v) for v in (x, y - 2.4, x + 26.676, y + 9.4)]
            ),
            NameObject("/A"): DictionaryObject(
                {
                    NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject(LINK_URL),
                }
            ),
        }
    )
    page[NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream


@pytest.mark.parametrize("path", ["fast", "layout"])
@pytest.mark.parametrize("multiline", [False, True], ids=["same-line", "preceding-line"])
@pytest.mark.parametrize(
    ("fake_bold", "glyph_text", "deduplicate", "prefix"),
    [
        pytest.param(True, None, True, "BOLD", id="fake-bold"),
        pytest.param(False, "ffi", True, "ffi", id="ligature"),
        pytest.param(False, "e\u0301", True, "e\u0301", id="combining-sequence"),
        pytest.param(False, None, True, "BOLD", id="ordinary-control"),
        pytest.param(True, None, False, "BBOOLLDD", id="disabled-dedup-control"),
    ],
)
def test_pdf_link_offset_follows_decoded_text(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    multiline: bool,
    fake_bold: bool,
    glyph_text: str | None,
    deduplicate: bool,
    prefix: str,
) -> None:
    """Retain a link's text and position after transforming preceding glyphs."""
    monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "3" if deduplicate else "0")
    stream = _pdf_with_transformed_prefix(
        fake_bold=fake_bold, multiline=multiline, glyph_text=glyph_text
    )

    if path == "fast":
        elements = partition_pdf(file=stream, strategy="fast", languages=["eng"])
        assert len(elements) == 1
        text = elements[0].text
        assert text == f"{prefix} LINK"
        links = elements[0].metadata.links
    else:
        layouts, page_links = process_data_with_pdfminer(file=stream, dpi=72)
        assert len(layouts) == len(page_links) == 1
        text = "".join(layouts[0].texts)
        assert " ".join(text.split()) == f"{prefix} LINK"
        links = page_links[0]

    assert links is not None
    assert len(links) == 1
    link = links[0]
    assert link["url"] == LINK_URL
    assert link["text"] == "LINK"
    assert link["start_index"] == text.index("LINK")
    assert text[link["start_index"] : link["start_index"] + len(link["text"])] == "LINK"
