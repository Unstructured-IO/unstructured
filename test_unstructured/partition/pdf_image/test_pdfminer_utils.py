from importlib import reload
from unittest.mock import MagicMock, patch

from pdfminer.layout import LTChar, LTContainer, LTFigure, LTLayoutContainer, LTTextLine
from pdfminer.pdftypes import PDFStream

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.pdf import (
    _extract_font_sizes_from_text_obj,
    _get_representative_font_size,
    _infer_category_depth_from_font_size,
    partition_pdf,
)
from unstructured.partition.pdf_image.pdfminer_utils import (
    CustomPDFPageInterpreter,
    _is_duplicate_char,
    deduplicate_chars_in_text_line,
    extract_text_objects,
    get_text_with_deduplication,
)
from unstructured.partition.utils import config as partition_config


def _make_char():
    return LTChar(
        matrix=(1, 0, 0, 1, 0, 0),
        font=MagicMock(),
        fontsize=12,
        scaling=1,
        rise=0,
        text="x",
        textwidth=10,
        textdisp=(0, 1),
        ncs=MagicMock(),
        graphicstate=MagicMock(),
    )


def _make_interpreter(cur_item):
    interp = object.__new__(CustomPDFPageInterpreter)
    interp.device = MagicMock()
    interp.device.cur_item = cur_item
    interp.textstate = MagicMock()
    interp.graphicstate = MagicMock()
    return interp


def _make_char_with_bbox(x0=0, y0=0, x1=10, y1=12):
    """Create LTChar with specific bounding box for font size testing.

    Font size is calculated from character height: y1 - y0
    """
    return LTChar(
        matrix=(1, 0, 0, 1, 0, 0),
        font=MagicMock(),
        fontsize=12,  # This is ignored by extraction logic
        scaling=1,
        rise=0,
        text="x",
        textwidth=10,
        textdisp=(0, 1),
        ncs=MagicMock(),
        graphicstate=MagicMock(),
    )


def test_patch_render_mode_only_new_chars():
    """Only chars added after the snapshot index should be patched."""
    page = LTLayoutContainer(bbox=(0, 0, 100, 100))
    interp = _make_interpreter(page)

    old_char = _make_char()
    page.add(old_char)

    interp.textstate.render = 3
    interp._patch_current_chars_with_render_mode(start=1)

    assert not hasattr(old_char, "rendermode")


def test_patch_render_mode_correct_value():
    """Chars in the patched range should get the current render mode."""
    page = LTLayoutContainer(bbox=(0, 0, 100, 100))
    interp = _make_interpreter(page)

    char = _make_char()
    page.add(char)

    interp.textstate.render = 3
    interp._patch_current_chars_with_render_mode(start=0)

    assert char.rendermode == 3


def test_patch_render_mode_preserved_after_figure_with_text():
    """When cur_item reverts to the page after a figure that contained text ops,
    previously patched chars must keep their original render mode."""
    page = LTLayoutContainer(bbox=(0, 0, 100, 100))
    interp = _make_interpreter(page)

    # Text op on page with render_mode=0
    char_a = _make_char()
    page.add(char_a)
    interp.textstate.render = 0
    interp._patch_current_chars_with_render_mode(start=0)

    # begin_figure — cur_item switches to figure
    figure = LTFigure("test", (0, 0, 50, 50), (1, 0, 0, 1, 0, 0))
    interp.device.cur_item = figure

    # Text op inside figure
    fig_char = _make_char()
    figure.add(fig_char)
    interp._patch_current_chars_with_render_mode(start=0)

    # end_figure — cur_item reverts to page
    interp.device.cur_item = page

    # Render mode changes, new text op on page
    interp.textstate.render = 3
    char_b = _make_char()
    page.add(char_b)
    interp._patch_current_chars_with_render_mode(start=1)

    assert char_a.rendermode == 0
    assert char_b.rendermode == 3


def test_do_TJ_snapshots_before_super():
    """do_TJ should snapshot len(objs) before super() adds chars,
    so only the newly added chars are patched."""
    page = LTLayoutContainer(bbox=(0, 0, 100, 100))
    interp = _make_interpreter(page)

    old_char = _make_char()
    page.add(old_char)
    old_char.rendermode = 0

    new_char = _make_char()

    def fake_super_do_TJ(self, seq):
        page.add(new_char)

    interp.textstate.render = 3
    interp.textstate.font = MagicMock()
    with patch.object(CustomPDFPageInterpreter.__bases__[0], "do_TJ", fake_super_do_TJ):
        interp.do_TJ([b"test"])

    assert old_char.rendermode == 0
    assert new_char.rendermode == 3


def test_extract_text_objects_nested_containers():
    """Test extract_text_objects with nested LTContainers."""
    # Mock LTTextLine objects
    mock_text_line1 = MagicMock(spec=LTTextLine)
    mock_text_line2 = MagicMock(spec=LTTextLine)

    # Mock inner container containing one LTTextLine
    mock_inner_container = MagicMock(spec=LTContainer)
    mock_inner_container.__iter__.return_value = [mock_text_line2]

    # Mock outer container containing another LTTextLine and the inner container
    mock_outer_container = MagicMock(spec=LTContainer)
    mock_outer_container.__iter__.return_value = [mock_text_line1, mock_inner_container]

    # Call the function with the outer container
    result = extract_text_objects(mock_outer_container)

    # Assert both text line objects are extracted, even from nested containers
    assert len(result) == 2
    assert mock_text_line1 in result
    assert mock_text_line2 in result


# -- Tests for character deduplication (fake bold fix) --


def _create_mock_ltchar(
    text: str, x0: float, y0: float, width: float = 6.0, height: float = 2.0
) -> MagicMock:
    """Helper to create a mock LTChar with specified text and position.

    Includes x1, y1 so _is_duplicate_char overlap logic works (fake-bold detection
    uses bounding box overlap). Default width/height give overlap ratio > 0.5 for
    chars within threshold distance.
    """
    mock_char = MagicMock(spec=LTChar)
    mock_char.get_text.return_value = text
    mock_char.x0 = x0
    mock_char.y0 = y0
    mock_char.x1 = x0 + width
    mock_char.y1 = y0 + height
    return mock_char


class TestIsDuplicateChar:
    """Tests for _is_duplicate_char function."""

    def test_same_char_same_position_is_duplicate(self):
        """Two identical characters at the same position should be duplicates."""
        char1 = _create_mock_ltchar("A", 10.0, 20.0)
        char2 = _create_mock_ltchar("A", 10.0, 20.0)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is True

    def test_same_char_close_position_is_duplicate(self):
        """Two identical characters at close positions should be duplicates."""
        char1 = _create_mock_ltchar("B", 10.0, 20.0)
        char2 = _create_mock_ltchar("B", 11.5, 21.0)  # Within 3.0 threshold
        assert _is_duplicate_char(char1, char2, threshold=3.0) is True

    def test_same_char_far_position_not_duplicate(self):
        """Two identical characters at far positions should not be duplicates."""
        char1 = _create_mock_ltchar("C", 10.0, 20.0)
        char2 = _create_mock_ltchar("C", 15.0, 20.0)  # 5.0 > 3.0 threshold
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

    def test_different_chars_same_position_not_duplicate(self):
        """Two different characters at the same position should not be duplicates."""
        char1 = _create_mock_ltchar("A", 10.0, 20.0)
        char2 = _create_mock_ltchar("B", 10.0, 20.0)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

    def test_threshold_boundary(self):
        """Test behavior at exact threshold boundary."""
        char1 = _create_mock_ltchar("X", 10.0, 20.0)
        char2 = _create_mock_ltchar("X", 13.0, 20.0)  # Exactly at threshold
        # At threshold means NOT within threshold (uses < not <=)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

        char3 = _create_mock_ltchar("X", 12.9, 20.0)  # Just under threshold
        assert _is_duplicate_char(char1, char3, threshold=3.0) is True


class TestDeduplicateCharsInTextLine:
    """Tests for deduplicate_chars_in_text_line function."""

    def test_no_duplicates_returns_original(self):
        """Text line without duplicates should return original text."""
        chars = [
            _create_mock_ltchar("H", 10.0, 20.0),
            _create_mock_ltchar("i", 15.0, 20.0),
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)
        mock_text_line.get_text.return_value = "Hi"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "Hi"

    def test_fake_bold_duplicates_removed(self):
        """Fake bold text (each char doubled) should be deduplicated."""
        # Simulates "BOLD" rendered as "BBOOLLDD" with duplicate positions
        chars = [
            _create_mock_ltchar("B", 10.0, 20.0),
            _create_mock_ltchar("B", 10.5, 20.0),  # Duplicate
            _create_mock_ltchar("O", 20.0, 20.0),
            _create_mock_ltchar("O", 20.5, 20.0),  # Duplicate
            _create_mock_ltchar("L", 30.0, 20.0),
            _create_mock_ltchar("L", 30.5, 20.0),  # Duplicate
            _create_mock_ltchar("D", 40.0, 20.0),
            _create_mock_ltchar("D", 40.5, 20.0),  # Duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "BOLD"

    def test_threshold_zero_disables_deduplication(self):
        """Setting threshold to 0 should disable deduplication."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.get_text.return_value = "BBOOLLDD"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=0)
        assert result == "BBOOLLDD"

    def test_negative_threshold_disables_deduplication(self):
        """Setting negative threshold should disable deduplication."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.get_text.return_value = "BBOOLLDD"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=-1.0)
        assert result == "BBOOLLDD"

    def test_empty_text_line(self):
        """Empty text line should return original text."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter([])
        mock_text_line.get_text.return_value = ""

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == ""

    def test_legitimate_repeated_chars_preserved(self):
        """Legitimate repeated characters (different positions) should be preserved."""
        # "AA" where both A's are at different positions
        chars = [
            _create_mock_ltchar("A", 10.0, 20.0),
            _create_mock_ltchar("A", 20.0, 20.0),  # Different position, not duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "AA"


class TestGetTextWithDeduplication:
    """Tests for get_text_with_deduplication function."""

    def test_with_text_line(self):
        """Should properly deduplicate text from LTTextLine."""
        chars = [
            _create_mock_ltchar("H", 10.0, 20.0),
            _create_mock_ltchar("H", 10.5, 20.0),  # Duplicate
            _create_mock_ltchar("i", 20.0, 20.0),
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = get_text_with_deduplication(mock_text_line, threshold=3.0)
        assert result == "Hi"

    def test_with_container(self):
        """Should handle LTContainer with nested LTTextLine."""
        chars = [
            _create_mock_ltchar("T", 10.0, 20.0),
            _create_mock_ltchar("T", 10.5, 20.0),  # Duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        mock_container = MagicMock(spec=LTContainer)
        mock_container.__iter__ = lambda self: iter([mock_text_line])

        result = get_text_with_deduplication(mock_container, threshold=3.0)
        assert result == "T"

    def test_with_generic_object(self):
        """Should fall back to get_text() for non-standard objects."""
        mock_obj = MagicMock()
        mock_obj.get_text.return_value = "fallback text"

        result = get_text_with_deduplication(mock_obj, threshold=3.0)
        assert result == "fallback text"

    def test_without_get_text(self):
        """Should return empty string for objects without get_text."""
        mock_obj = MagicMock(spec=[])  # No get_text method

        result = get_text_with_deduplication(mock_obj, threshold=3.0)
        assert result == ""


# -- Integration tests for fake-bold PDF deduplication --


class TestFakeBoldPdfIntegration:
    """Integration tests for fake-bold PDF deduplication using real PDF files.

    The test PDF (fake-bold-sample.pdf) contains text rendered with the "fake bold"
    technique where each character is drawn twice at slightly offset positions.
    This causes text extraction to show doubled characters (e.g., "BBOOLLDD" instead
    of "BOLD") unless deduplication is applied.
    """

    def test_fake_bold_pdf_without_deduplication_shows_doubled_chars(self, monkeypatch):
        """Test that extraction WITHOUT deduplication shows doubled characters.

        When PDF_CHAR_DUPLICATE_THRESHOLD is set to 0, deduplication is disabled
        and the raw text shows the fake-bold doubled characters.
        """
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "0")
        reload(partition_config)

        filename = example_doc_path("pdf/fake-bold-sample.pdf")
        elements = partition_pdf(filename=filename, strategy="fast")
        extracted_text = " ".join([el.text for el in elements])

        # Without deduplication, fake-bold text appears with doubled characters
        assert "BBOOLLDD" in extracted_text, (
            "Without deduplication, fake-bold text should show doubled characters "
            "like 'BBOOLLDD' instead of 'BOLD'"
        )

    def test_fake_bold_pdf_with_deduplication_shows_clean_text(self, monkeypatch):
        """Test that extraction WITH deduplication shows clean text.

        When PDF_CHAR_DUPLICATE_THRESHOLD is set to default (2.0), deduplication
        removes the duplicate characters and produces clean, readable text.
        """
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "2.0")
        reload(partition_config)

        filename = example_doc_path("pdf/fake-bold-sample.pdf")
        elements = partition_pdf(filename=filename, strategy="fast")
        extracted_text = " ".join([el.text for el in elements])

        # With deduplication, fake-bold text should be clean (no doubled chars)
        assert "BOLD" in extracted_text, (
            "With deduplication, text should contain clean 'BOLD' not 'BBOOLLDD'"
        )
        # Verify the doubled pattern is NOT present in the deduplicated fake-bold section
        # Note: The PDF contains 'BBOOLLDD' as explanatory text, so we check for
        # the specific pattern that would appear if deduplication failed on the
        # fake-bold rendered text (e.g., "TTEEXXTT" from "TEXT")
        assert "TTEEXXTT" not in extracted_text, (
            "With deduplication, fake-bold 'TEXT' should not appear as 'TTEEXXTT'"
        )

    def test_fake_bold_deduplication_reduces_text_length(self, monkeypatch):
        """Test that deduplication reduces text length for fake-bold PDFs.

        Compares extraction with and without deduplication to verify that
        the deduplicated text is shorter due to removal of duplicate characters.
        """
        filename = example_doc_path("pdf/fake-bold-sample.pdf")

        # Extract WITHOUT deduplication (threshold=0)
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "0")
        reload(partition_config)
        elements_no_dedup = partition_pdf(filename=filename, strategy="fast")
        text_no_dedup = " ".join([el.text for el in elements_no_dedup])

        # Extract WITH deduplication (threshold=2.0)
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "2.0")
        reload(partition_config)
        elements_with_dedup = partition_pdf(filename=filename, strategy="fast")
        text_with_dedup = " ".join([el.text for el in elements_with_dedup])

        # Deduplicated text should be shorter than non-deduplicated text
        assert len(text_with_dedup) < len(text_no_dedup), (
            f"Deduplicated text ({len(text_with_dedup)} chars) should be shorter "
            f"than non-deduplicated text ({len(text_no_dedup)} chars)"
        )


# -- Tests for embedded CMap stream parsing --


class TestParseEmbeddedCmapStream:
    """Unit tests for _parse_embedded_cmap_stream.

    pdfminer.six does not parse embedded Encoding CMap streams for CIDFonts.
    _parse_embedded_cmap_stream is our workaround that extracts code-to-CID
    mappings and writing mode from the raw CMap stream bytes.
    """

    @staticmethod
    def _parse(data: bytes):
        from unstructured.partition.pdf_image.pdfminer_utils import _parse_embedded_cmap_stream

        return _parse_embedded_cmap_stream(data)

    def test_vertical_wmode_is_preserved(self):
        """Embedded CMaps with WMode=1 (vertical) should produce a vertical CMap."""
        data = b"""
/WMode 1
1 begincodespacerange
<00> <0A>
endcodespacerange
1 begincidrange
<00> <0A> 0
endcidrange
"""
        cmap = self._parse(data)
        assert cmap.is_vertical() is True
        assert len(cmap.code2cid) == 11

    def test_horizontal_wmode_is_default(self):
        """CMaps without WMode or with WMode=0 should produce a horizontal CMap."""
        data = b"""
1 begincodespacerange
<00> <05>
endcodespacerange
1 begincidrange
<00> <05> 0
endcidrange
"""
        cmap = self._parse(data)
        assert cmap.is_vertical() is False

    def test_oversized_stream_returns_empty_cmap(self):
        """Streams exceeding the size cap should be rejected before any parsing."""
        from unstructured.partition.pdf_image.pdfminer_utils import _MAX_CMAP_STREAM_BYTES

        data = b"x" * (_MAX_CMAP_STREAM_BYTES + 1)
        cmap = self._parse(data)
        assert not cmap.code2cid

    def test_reversed_range_is_skipped(self):
        """A begincidrange where end < start should be silently skipped."""
        data = b"""
1 begincodespacerange
<00> <FF>
endcodespacerange
1 begincidrange
<80> <10> 0
endcidrange
"""
        cmap = self._parse(data)
        assert not cmap.code2cid

    def test_mapping_cap_bounds_total_entries(self):
        """The total mapping count should be bounded across both cidrange and cidchar."""
        from unittest.mock import patch

        data = b"""
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
1 begincidrange
<0000> <FFFF> 0
endcidrange
"""
        # Use a small cap to verify bounding without allocating huge dicts
        with patch("unstructured.partition.pdf_image.pdfminer_utils._MAX_CODE2CID_MAPPINGS", 100):
            cmap = self._parse(data)
            assert not cmap.code2cid  # 65536 > 100: entire CMap discarded, not partial

    def test_mapping_budget_second_range_discards_entire_cmap(self):
        """If a later cidrange would exceed the cap, reject the whole map (no holes)."""
        from unittest.mock import patch

        data = b"""
1 begincodespacerange
<00> <19>
endcodespacerange
2 begincidrange
<00> <09> 0
<0A> <19> 10
endcidrange
"""
        with patch("unstructured.partition.pdf_image.pdfminer_utils._MAX_CODE2CID_MAPPINGS", 15):
            cmap = self._parse(data)
            assert not cmap.code2cid


class TestBoundedStreamDecode:
    """Tests for _decode_pdfstream_with_limit.

    Verifies that oversized embedded CMap streams are rejected *before* full
    materialization, and that the shared PDFStream object is never mutated.
    """

    def test_oversized_flate_stream_rejected_before_materialization(self):
        """A small compressed payload that expands past the limit should be rejected
        without fully materializing the output, and the stream should not be mutated."""
        import zlib

        from pdfminer.psparser import LIT

        from unstructured.partition.pdf_image.pdfminer_utils import (
            _decode_pdfstream_with_limit,
        )

        payload = zlib.compress(b"x" * 200)
        stream = PDFStream({"Filter": LIT("FlateDecode")}, payload)

        result = _decode_pdfstream_with_limit(stream, max_decoded_bytes=100)
        assert result is None
        # Stream object must not be mutated
        assert stream.get_rawdata() is not None
        assert stream.data is None

    def test_normal_stream_decodes_within_limit(self):
        """A stream that fits within the limit should decode successfully."""
        import zlib

        from pdfminer.psparser import LIT

        from unstructured.partition.pdf_image.pdfminer_utils import (
            _decode_pdfstream_with_limit,
        )

        content = b"begincidrange <00> <05> 0 endcidrange"
        payload = zlib.compress(content)
        stream = PDFStream({"Filter": LIT("FlateDecode")}, payload)

        result = _decode_pdfstream_with_limit(stream, max_decoded_bytes=1000)
        assert result == content

    def test_encrypted_stream_without_objid_returns_none(self):
        """Decipher requires objid/genno; missing values skip decode (no crash)."""
        from unstructured.partition.pdf_image.pdfminer_utils import (
            _decode_pdfstream_with_limit,
        )

        stream = PDFStream({}, b"encrypted-bytes", decipher=lambda *a: b"x")
        stream.objid = None
        stream.genno = 0
        assert _decode_pdfstream_with_limit(stream, max_decoded_bytes=1000) is None

        stream.objid = 1
        stream.genno = None
        assert _decode_pdfstream_with_limit(stream, max_decoded_bytes=1000) is None

    def test_uncompressed_stream_returns_raw(self):
        """A stream with no filters should return the raw data directly."""
        from unstructured.partition.pdf_image.pdfminer_utils import (
            _decode_pdfstream_with_limit,
        )

        content = b"begincidrange <00> <05> 0 endcidrange"
        stream = PDFStream({}, content)

        result = _decode_pdfstream_with_limit(stream, max_decoded_bytes=1000)
        assert result == content


class TestCustomPDFCIDFont:
    """Tests for CustomPDFCIDFont constructor-time CMap resolution."""

    def test_vertical_wmode_sets_font_vertical_flag(self):
        """A vertical embedded CMap (WMode=1) should set font.vertical=True and
        font.default_disp != 0 at construction time, not just on the CMap."""
        import zlib

        from pdfminer.pdfinterp import PDFResourceManager
        from pdfminer.psparser import LIT

        from unstructured.partition.pdf_image.pdfminer_utils import CustomPDFCIDFont

        cmap_data = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> def
/CMapName /Test-Vertical-H def
/CMapType 1 def
/WMode 1 def
1 begincodespacerange
<00> <0A>
endcodespacerange
1 begincidrange
<00> <0A> 0
endcidrange
endcmap
end
end"""

        encoding_stream = PDFStream(
            {
                "Type": LIT("CMap"),
                "CMapName": LIT("Test-Vertical-H"),
                "CIDSystemInfo": {
                    "Registry": b"Adobe",
                    "Ordering": b"Identity",
                    "Supplement": 0,
                },
                "Filter": LIT("FlateDecode"),
            },
            zlib.compress(cmap_data),
        )

        tounicode_data = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /Adobe-Identity-UCS def
/CMapType 2 def
1 begincodespacerange
<00> <FF>
endcodespacerange
1 beginbfrange
<00> <0A> <0041>
endbfrange
endcmap
end
end"""
        tounicode_stream = PDFStream({}, tounicode_data)

        spec = {
            "Type": LIT("Font"),
            "Subtype": LIT("CIDFontType2"),
            "BaseFont": LIT("TestSans"),
            "CIDSystemInfo": {
                "Registry": b"Adobe",
                "Ordering": b"Identity",
                "Supplement": 0,
            },
            "FontDescriptor": {
                "Type": LIT("FontDescriptor"),
                "FontName": LIT("TestSans"),
                "Flags": 32,
                "FontBBox": [0, -200, 1000, 800],
                "ItalicAngle": 0,
                "Ascent": 800,
                "Descent": -200,
                "CapHeight": 700,
                "StemV": 80,
            },
            "DW": 500,
            "Encoding": encoding_stream,
            "ToUnicode": tounicode_stream,
        }

        rsrcmgr = PDFResourceManager()
        font = CustomPDFCIDFont(rsrcmgr, spec, strict=False)

        assert font.cmap.is_vertical() is True
        assert font.vertical is True
        assert font.default_disp != 0


class TestCustomPDFResourceManager:
    """Tests for CustomPDFResourceManager font construction routing."""

    def test_returns_custom_cidfont_for_cid_subtypes(self):
        """CIDFontType2 fonts should be constructed as CustomPDFCIDFont."""
        from pdfminer.psparser import LIT

        from unstructured.partition.pdf_image.pdfminer_utils import (
            CustomPDFCIDFont,
            CustomPDFResourceManager,
        )

        cmap_data = b"""begincmap
1 begincodespacerange <00> <05> endcodespacerange
1 begincidrange <00> <05> 0 endcidrange
endcmap"""

        spec = {
            "Type": LIT("Font"),
            "Subtype": LIT("CIDFontType2"),
            "BaseFont": LIT("TestSans"),
            "CIDSystemInfo": {
                "Registry": b"Adobe",
                "Ordering": b"Identity",
                "Supplement": 0,
            },
            "FontDescriptor": {
                "Type": LIT("FontDescriptor"),
                "FontName": LIT("TestSans"),
                "Flags": 32,
                "FontBBox": [0, -200, 1000, 800],
                "ItalicAngle": 0,
                "Ascent": 800,
                "Descent": -200,
                "CapHeight": 700,
                "StemV": 80,
            },
            "DW": 500,
            "Encoding": PDFStream(
                {
                    "Type": LIT("CMap"),
                    "CMapName": LIT("Test-Custom-H"),
                    "CIDSystemInfo": {
                        "Registry": b"Adobe",
                        "Ordering": b"Identity",
                        "Supplement": 0,
                    },
                },
                cmap_data,
            ),
        }

        rsrcmgr = CustomPDFResourceManager()
        font = rsrcmgr.get_font(1, spec)

        assert isinstance(font, CustomPDFCIDFont)

    def test_caches_font_on_repeated_calls(self):
        """Repeated get_font calls with the same objid should return the cached instance."""
        from pdfminer.psparser import LIT

        from unstructured.partition.pdf_image.pdfminer_utils import (
            CustomPDFResourceManager,
        )

        cmap_data = b"""begincmap
1 begincodespacerange <00> <05> endcodespacerange
1 begincidrange <00> <05> 0 endcidrange
endcmap"""

        spec = {
            "Type": LIT("Font"),
            "Subtype": LIT("CIDFontType2"),
            "BaseFont": LIT("TestSans"),
            "CIDSystemInfo": {
                "Registry": b"Adobe",
                "Ordering": b"Identity",
                "Supplement": 0,
            },
            "FontDescriptor": {
                "Type": LIT("FontDescriptor"),
                "FontName": LIT("TestSans"),
                "Flags": 32,
                "FontBBox": [0, -200, 1000, 800],
                "ItalicAngle": 0,
                "Ascent": 800,
                "Descent": -200,
                "CapHeight": 700,
                "StemV": 80,
            },
            "DW": 500,
            "Encoding": PDFStream(
                {
                    "Type": LIT("CMap"),
                    "CMapName": LIT("Test-Custom-H"),
                    "CIDSystemInfo": {
                        "Registry": b"Adobe",
                        "Ordering": b"Identity",
                        "Supplement": 0,
                    },
                },
                cmap_data,
            ),
        }

        rsrcmgr = CustomPDFResourceManager()
        font1 = rsrcmgr.get_font(42, spec)
        font2 = rsrcmgr.get_font(42, spec)

        assert font1 is font2


# ================================================================================================
# Tests for PDF Heading Hierarchy Helper Functions
# ================================================================================================


def test_extract_font_sizes_empty_object():
    """Test _extract_font_sizes_from_text_obj with empty container."""
    container = LTLayoutContainer(bbox=(0, 0, 100, 100))

    result = _extract_font_sizes_from_text_obj(container)

    assert result == []


def test_extract_font_sizes_single_char():
    """Test _extract_font_sizes_from_text_obj with single character."""
    char = _make_char_with_bbox(x0=0, y0=0, x1=10, y1=12)

    result = _extract_font_sizes_from_text_obj(char)

    assert result == [12.0]


def test_extract_font_sizes_nested_container():
    """Test _extract_font_sizes_from_text_obj with nested containers."""
    # Create nested structure: Container -> TextLine -> Multiple chars
    container = LTLayoutContainer(bbox=(0, 0, 100, 100))
    text_line = LTTextLine(word_margin=0.1)

    char1 = _make_char_with_bbox(x0=0, y0=0, x1=10, y1=10)
    char2 = _make_char_with_bbox(x0=10, y0=0, x1=20, y1=12)
    char3 = _make_char_with_bbox(x0=20, y0=0, x1=30, y1=14)

    text_line.add(char1)
    text_line.add(char2)
    text_line.add(char3)
    container.add(text_line)

    result = _extract_font_sizes_from_text_obj(container)

    assert result == [10.0, 12.0, 14.0]


def test_extract_font_sizes_filters_zero_sizes():
    """Test _extract_font_sizes_from_text_obj filters zero/negative sizes."""
    container = LTLayoutContainer(bbox=(0, 0, 100, 100))

    char1 = _make_char_with_bbox(x0=0, y0=0, x1=10, y1=12)  # Valid: 12.0
    char2 = _make_char_with_bbox(x0=10, y0=10, x1=20, y1=10)  # Zero height
    char3 = _make_char_with_bbox(x0=20, y0=5, x1=30, y1=0)  # Negative height

    container.add(char1)
    container.add(char2)
    container.add(char3)

    result = _extract_font_sizes_from_text_obj(container)

    assert result == [12.0]


def test_extract_font_sizes_multiple_chars():
    """Test _extract_font_sizes_from_text_obj with multiple characters."""
    container = LTLayoutContainer(bbox=(0, 0, 100, 100))

    char1 = _make_char_with_bbox(x0=0, y0=0, x1=10, y1=10)
    char2 = _make_char_with_bbox(x0=10, y0=0, x1=20, y1=12)
    char3 = _make_char_with_bbox(x0=20, y0=0, x1=30, y1=14)

    container.add(char1)
    container.add(char2)
    container.add(char3)

    result = _extract_font_sizes_from_text_obj(container)

    assert result == [10.0, 12.0, 14.0]


def test_extract_font_sizes_no_ltchar_objects():
    """Test _extract_font_sizes_from_text_obj with non-text objects."""
    container = LTLayoutContainer(bbox=(0, 0, 100, 100))

    # Add a figure (non-text object)
    figure = LTFigure("test", (0, 0, 50, 50), (1, 0, 0, 1, 0, 0))
    container.add(figure)

    result = _extract_font_sizes_from_text_obj(container)

    assert result == []


def test_representative_font_size_empty_list():
    """Test _get_representative_font_size with empty list."""
    result = _get_representative_font_size([])

    assert result is None


def test_representative_font_size_single_element():
    """Test _get_representative_font_size with single element."""
    result = _get_representative_font_size([12.0])

    assert result == 12.0


def test_representative_font_size_odd_length():
    """Test _get_representative_font_size with odd-length list."""
    result = _get_representative_font_size([10.0, 12.0, 14.0])

    assert result == 12.0  # Middle element


def test_representative_font_size_even_length():
    """Test _get_representative_font_size with even-length list.

    This tests the P1 fix scenario: when calculating median from even-length list,
    the result is the average of middle two elements, which may not exist in the
    original list (floating-point median edge case).
    """
    result = _get_representative_font_size([10.0, 12.0, 14.0, 16.0])

    assert result == 13.0  # Average of 12.0 and 14.0


def test_representative_font_size_unsorted_input():
    """Test _get_representative_font_size with unsorted input."""
    result = _get_representative_font_size([14.0, 10.0, 12.0])

    assert result == 12.0  # Function should sort internally


def test_category_depth_non_title_returns_none():
    """Test _infer_category_depth_from_font_size returns None for non-title elements."""
    page_font_sizes = {10.0: 50, 12.0: 10, 14.0: 5}

    result = _infer_category_depth_from_font_size(
        font_size=14.0, page_font_sizes=page_font_sizes, is_title=False
    )

    assert result is None


def test_category_depth_none_font_size_returns_none():
    """Test _infer_category_depth_from_font_size returns None for None font_size."""
    page_font_sizes = {10.0: 50, 12.0: 10, 14.0: 5}

    result = _infer_category_depth_from_font_size(
        font_size=None, page_font_sizes=page_font_sizes, is_title=True
    )

    assert result is None


def test_category_depth_empty_page_font_sizes_returns_none():
    """Test _infer_category_depth_from_font_size returns None for empty page_font_sizes."""
    result = _infer_category_depth_from_font_size(
        font_size=12.0, page_font_sizes={}, is_title=True
    )

    assert result is None


def test_category_depth_body_text_returns_none():
    """Test _infer_category_depth_from_font_size returns None for body text.

    Body text is identified as the most common font size on the page.
    """
    page_font_sizes = {10.0: 5, 12.0: 100, 14.0: 10}  # 12.0 is most common

    result = _infer_category_depth_from_font_size(
        font_size=12.0, page_font_sizes=page_font_sizes, is_title=True
    )

    assert result is None  # Body text should not get category_depth


def test_category_depth_largest_heading_returns_1():
    """Test _infer_category_depth_from_font_size returns 1 for largest heading."""
    page_font_sizes = {12.0: 80, 14.0: 10, 18.0: 5}  # 12.0 is body, 18.0 is largest heading

    result = _infer_category_depth_from_font_size(
        font_size=18.0, page_font_sizes=page_font_sizes, is_title=True
    )

    assert result == 1


def test_category_depth_multiple_heading_levels():
    """Test _infer_category_depth_from_font_size with multiple heading levels."""
    page_font_sizes = {10.0: 80, 12.0: 15, 14.0: 10, 16.0: 5, 18.0: 3}
    # 10.0 is body text (most common)
    # Heading hierarchy: 18.0 > 16.0 > 14.0 > 12.0

    assert (
        _infer_category_depth_from_font_size(
            font_size=18.0, page_font_sizes=page_font_sizes, is_title=True
        )
        == 1
    )
    assert (
        _infer_category_depth_from_font_size(
            font_size=16.0, page_font_sizes=page_font_sizes, is_title=True
        )
        == 2
    )
    assert (
        _infer_category_depth_from_font_size(
            font_size=14.0, page_font_sizes=page_font_sizes, is_title=True
        )
        == 3
    )
    assert (
        _infer_category_depth_from_font_size(
            font_size=12.0, page_font_sizes=page_font_sizes, is_title=True
        )
        == 4
    )


def test_category_depth_closest_match_logic():
    """Test _infer_category_depth_from_font_size with closest-match logic.

    This tests the P1 fix: when font_size is a floating-point median that doesn't
    exist in page_font_sizes keys (e.g., 13.0 = average of 12.0 and 14.0), the
    function should use the closest match within tolerance instead of failing.
    """
    page_font_sizes = {10.0: 60, 12.0: 20, 14.0: 10, 16.0: 5}
    # 10.0 is body text
    # Heading hierarchy: 16.0 > 14.0 > 12.0

    # Test median that doesn't exist in keys (13.0 is between 12.0 and 14.0)
    result = _infer_category_depth_from_font_size(
        font_size=13.0, page_font_sizes=page_font_sizes, is_title=True
    )

    # Should match closest heading (either 12.0 or 14.0) within 1pt tolerance
    assert result in [2, 3]  # Either 14.0 (rank 2) or 12.0 (rank 3)


def test_category_depth_caps_at_6():
    """Test _infer_category_depth_from_font_size caps at 6 levels."""
    # Create 10 different heading sizes
    page_font_sizes = {
        10.0: 100,  # Body text (most common)
        12.0: 5,
        14.0: 5,
        16.0: 5,
        18.0: 5,
        20.0: 5,
        22.0: 5,
        24.0: 5,
        26.0: 5,
        28.0: 5,
        30.0: 5,
    }

    # Test the 7th, 8th, 9th, 10th largest headings - all should cap at 6
    result_7th = _infer_category_depth_from_font_size(
        font_size=24.0, page_font_sizes=page_font_sizes, is_title=True
    )
    result_10th = _infer_category_depth_from_font_size(
        font_size=12.0, page_font_sizes=page_font_sizes, is_title=True
    )

    assert result_7th == 6  # Should cap at 6, not 7
    assert result_10th == 6  # Should cap at 6, not 10
