import os
import re
import tempfile
import zlib
from typing import BinaryIO, List, Mapping, Optional, Tuple, Union

from pdfminer import settings as pdfminer_settings
from pdfminer.cmapdb import CMap, CMapDB
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar, LTContainer, LTImage, LTItem, LTTextLine
from pdfminer.pdffont import PDFCIDFont, PDFFontError
from pdfminer.pdfinterp import LITERAL_FONT, PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import (
    LITERALS_ASCII85_DECODE,
    LITERALS_ASCIIHEX_DECODE,
    LITERALS_FLATE_DECODE,
    PDFStream,
    resolve1,
)
from pdfminer.psexceptions import PSSyntaxError
from pdfminer.psparser import literal_name
from pydantic import BaseModel

from unstructured.logger import logger
from unstructured.partition.utils.config import env_config
from unstructured.utils import requires_dependencies

_RE_CIDRANGE_BLOCK = re.compile(rb"begincidrange\s+(.*?)\s+endcidrange", re.DOTALL)
_RE_CIDRANGE_ENTRY = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s+(\d+)")
_RE_CIDCHAR_BLOCK = re.compile(rb"begincidchar\s+(.*?)\s+endcidchar", re.DOTALL)
_RE_CIDCHAR_ENTRY = re.compile(rb"<([0-9A-Fa-f]+)>\s+(\d+)")
_RE_WMODE = re.compile(rb"/WMode\s+(\d+)")

# Cap on decompressed CMap stream size to bound regex/parse cost before any mapping
# cap kicks in. Real-world embedded CMaps are typically a few hundred bytes; even
# large CJK CMaps are well under 100 KB.
_MAX_CMAP_STREAM_BYTES = 1_000_000

# Cap on total code-to-CID mappings to prevent malicious PDFs from causing excessive
# memory/CPU usage via huge begincidrange spans. 131072 covers all real-world fonts
# (single-byte: max 256, double-byte CJK: typically ~20-30K glyphs).
_MAX_CODE2CID_MAPPINGS = 131072


def _parse_embedded_cmap_stream(data: bytes) -> CMap:
    """Parse an embedded CMap stream into a CMap with a populated code2cid mapping.

    pdfminer.six does not parse embedded Encoding CMap streams for CIDFonts — it only
    looks up the CMap name in its predefined database. When a PDF (e.g. produced by
    Prince XML) embeds a custom CMap as a stream, pdfminer silently falls back to an
    empty CMap and all text using that font is lost.

    This function parses the begincidrange/begincidchar sections from the raw CMap
    stream and builds the code2cid dict that CMap.decode() uses. It also extracts
    WMode (writing mode: 0=horizontal, 1=vertical) when present.
    """
    if len(data) > _MAX_CMAP_STREAM_BYTES:
        logger.warning(
            "Embedded CMap stream too large (%d bytes, limit %d), skipping",
            len(data),
            _MAX_CMAP_STREAM_BYTES,
        )
        return CMap()

    code2cid: dict[int, object] = {}
    total_mappings = 0

    for match in _RE_CIDRANGE_BLOCK.finditer(data):
        entries = _RE_CIDRANGE_ENTRY.findall(match.group(1))
        for start_hex, end_hex, cid_str in entries:
            start_bytes = bytes.fromhex(start_hex.decode("ascii"))
            end_bytes = bytes.fromhex(end_hex.decode("ascii"))
            start_cid = int(cid_str)
            code_len = len(start_bytes)
            start_val = int.from_bytes(start_bytes, "big")
            end_val = int.from_bytes(end_bytes, "big")

            if end_val < start_val:
                continue
            range_size = end_val - start_val + 1
            if total_mappings + range_size > _MAX_CODE2CID_MAPPINGS:
                logger.warning(
                    "Embedded CMap would exceed %d mappings; discarding partial CMap",
                    _MAX_CODE2CID_MAPPINGS,
                )
                return CMap()
            for i in range(range_size):
                code_val = start_val + i
                cid = start_cid + i
                if code_len == 1:
                    code2cid[code_val] = cid
                else:
                    code_bytes = code_val.to_bytes(code_len, "big")
                    d = code2cid
                    for b in code_bytes[:-1]:
                        if b not in d:
                            d[b] = {}
                        d = d[b]  # type: ignore[assignment]
                    d[code_bytes[-1]] = cid
            total_mappings += range_size

    for match in _RE_CIDCHAR_BLOCK.finditer(data):
        entries = _RE_CIDCHAR_ENTRY.findall(match.group(1))
        for code_hex, cid_str in entries:
            if total_mappings >= _MAX_CODE2CID_MAPPINGS:
                logger.warning(
                    "Embedded CMap exceeded %d mappings; discarding partial CMap",
                    _MAX_CODE2CID_MAPPINGS,
                )
                return CMap()
            code_bytes = bytes.fromhex(code_hex.decode("ascii"))
            cid = int(cid_str)
            if len(code_bytes) == 1:
                code2cid[code_bytes[0]] = cid
            else:
                d = code2cid
                for b in code_bytes[:-1]:
                    if b not in d:
                        d[b] = {}
                    d = d[b]  # type: ignore[assignment]
                d[code_bytes[-1]] = cid
            total_mappings += 1

    cmap = CMap()
    cmap.code2cid = code2cid

    wmode_match = _RE_WMODE.search(data)
    if wmode_match and int(wmode_match.group(1)) != 0:
        cmap.attrs["WMode"] = int(wmode_match.group(1))

    return cmap


def _flate_decode_with_limit(data: bytes, limit: int) -> Optional[bytes]:
    """Decompress Flate data with a hard output size limit.

    Returns None if the decompressed output would exceed `limit` bytes,
    without fully materializing the result.
    """
    decomp = zlib.decompressobj()
    out = bytearray()
    try:
        out.extend(decomp.decompress(data, limit + 1))
        if len(out) > limit or decomp.unconsumed_tail:
            return None
        out.extend(decomp.flush(limit + 1 - len(out)))
        if len(out) > limit:
            return None
    except zlib.error:
        return None
    return bytes(out)


def _decode_pdfstream_with_limit(stream: PDFStream, max_decoded_bytes: int) -> Optional[bytes]:
    """Decode a PDFStream with a hard output size limit, without mutating the stream.

    Unlike PDFStream.get_data(), this never assigns to stream.data or stream.rawdata.
    Returns None if the decoded output exceeds the limit or uses an unsupported filter.
    """
    raw = stream.get_rawdata()
    if raw is None:
        # Stream was already decoded elsewhere; check the cached result.
        data = stream.data
        if data is None or len(data) > max_decoded_bytes:
            return None
        return data

    data = raw

    if stream.decipher:
        if stream.objid is None or stream.genno is None:
            logger.debug("Encrypted CMap stream missing objid/genno; skipping")
            return None
        data = stream.decipher(stream.objid, stream.genno, data, stream.attrs)

    for filt, params in stream.get_filters():
        if filt in LITERALS_FLATE_DECODE:
            result = _flate_decode_with_limit(data, max_decoded_bytes)
            if result is None:
                logger.warning(
                    "Embedded CMap stream exceeded %d bytes during decompression; skipping",
                    max_decoded_bytes,
                )
                return None
            data = result
        elif filt in LITERALS_ASCII85_DECODE:
            from pdfminer.ascii85 import ascii85decode

            data = ascii85decode(data)
        elif filt in LITERALS_ASCIIHEX_DECODE:
            from pdfminer.ascii85 import asciihexdecode

            data = asciihexdecode(data)
        else:
            logger.debug("Unsupported embedded CMap filter %r; skipping", filt)
            return None

        if len(data) > max_decoded_bytes:
            logger.warning(
                "Embedded CMap stream exceeded %d bytes after filter; skipping",
                max_decoded_bytes,
            )
            return None

    return data


class CustomPDFCIDFont(PDFCIDFont):
    """A CIDFont subclass that handles embedded Encoding CMap streams at construction time.

    pdfminer.six's PDFCIDFont.get_cmap_from_spec only looks up CMap names in its
    predefined database. When a PDF embeds a custom CMap as a stream, pdfminer falls
    back to an empty CMap and all text is lost.

    This subclass overrides get_cmap_from_spec to parse the embedded stream when the
    name lookup fails. Because this runs during __init__, all constructor-time state
    (vertical mode, widths, displacements) is derived from the correct CMap.
    """

    def get_cmap_from_spec(self, spec: Mapping, strict: bool):
        cmap_name = self._get_cmap_name(spec, strict)
        try:
            return CMapDB.get_cmap(cmap_name)
        except CMapDB.CMapNotFound as e:
            encoding = resolve1(spec.get("Encoding"))
            if isinstance(encoding, PDFStream):
                try:
                    data = _decode_pdfstream_with_limit(encoding, _MAX_CMAP_STREAM_BYTES)
                    if data is not None:
                        cmap = _parse_embedded_cmap_stream(data)
                        if cmap.code2cid:
                            logger.debug(
                                "Parsed embedded CMap stream %r (%d code mappings)",
                                cmap_name,
                                len(cmap.code2cid),
                            )
                            return cmap
                except (
                    ValueError,
                    KeyError,
                    TypeError,
                    UnicodeDecodeError,
                    zlib.error,
                    PSSyntaxError,
                ) as exc:
                    logger.warning(
                        "Failed to parse embedded CMap stream %r: %s",
                        cmap_name,
                        exc,
                        exc_info=True,
                    )
            if strict:
                raise PDFFontError(e) from e
            return CMap()


class CustomPDFResourceManager(PDFResourceManager):
    """A resource manager that uses CustomPDFCIDFont for CID font construction.

    This ensures embedded CMap streams are resolved during font construction,
    not after, so all constructor-time state (WMode, widths) is correct.
    """

    def get_font(self, objid, spec):
        subtype = literal_name(spec["Subtype"]) if "Subtype" in spec else "Type1"

        if subtype in ("CIDFontType0", "CIDFontType2"):
            if objid and objid in self._cached_fonts:
                return self._cached_fonts[objid]
            if pdfminer_settings.STRICT and spec.get("Type") is not LITERAL_FONT:
                raise PDFFontError("Type is not /Font")
            font = CustomPDFCIDFont(self, spec)
            if objid and self.caching:
                self._cached_fonts[objid] = font
            return font

        return super().get_font(objid, spec)


class CustomPDFPageInterpreter(PDFPageInterpreter):
    """a custom pdfminer page interpreter that adds character render mode information to LTChar
    object as `rendermode` attribute. This is intended to be used to detect invisible text."""

    def _patch_current_chars_with_render_mode(self, start: int):
        """Add render_mode to LTChar objects added since index `start`."""
        cur_item = getattr(self.device, "cur_item", None)
        if not cur_item:
            return
        render_mode = self.textstate.render
        for obj in getattr(cur_item, "_objs", ())[start:]:
            if isinstance(obj, LTChar):
                obj.rendermode = render_mode

    def do_TJ(self, seq):
        start = len(getattr(getattr(self.device, "cur_item", None), "_objs", ()))
        super().do_TJ(seq)
        self._patch_current_chars_with_render_mode(start)


class PDFMinerConfig(BaseModel):
    line_overlap: Optional[float] = None
    word_margin: Optional[float] = None
    line_margin: Optional[float] = None
    char_margin: Optional[float] = None


def init_pdfminer(pdfminer_config: Optional[PDFMinerConfig] = None):
    rsrcmgr = CustomPDFResourceManager()

    laparams_kwargs = pdfminer_config.model_dump(exclude_none=True) if pdfminer_config else {}
    laparams = LAParams(**laparams_kwargs)

    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = CustomPDFPageInterpreter(rsrcmgr, device)

    return device, interpreter


def extract_image_objects(parent_object: LTItem) -> List[LTImage]:
    """Recursively extracts image objects from a given parent object in a PDF document."""
    objects = []

    if isinstance(parent_object, LTImage):
        objects.append(parent_object)
    elif isinstance(parent_object, LTContainer):
        for child in parent_object:
            objects.extend(extract_image_objects(child))

    return objects


def extract_text_objects(parent_object: LTItem) -> List[LTTextLine]:
    """Recursively extracts text objects from a given parent object in a PDF document."""
    objects = []

    if isinstance(parent_object, LTTextLine):
        objects.append(parent_object)
    elif isinstance(parent_object, LTContainer):
        for child in parent_object:
            objects.extend(extract_text_objects(child))

    return objects


def rect_to_bbox(
    rect: Tuple[float, float, float, float],
    height: float,
) -> Tuple[float, float, float, float]:
    """
    Converts a PDF rectangle coordinates (x1, y1, x2, y2) to a bounding box in the specified
    coordinate system where the vertical axis is measured from the top of the page.

    Args:
        rect (Tuple[float, float, float, float]): A tuple representing a PDF rectangle
            coordinates (x1, y1, x2, y2).
        height (float): The height of the page in the specified coordinate system.

    Returns:
        Tuple[float, float, float, float]: A tuple representing the bounding box coordinates
        (x1, y1, x2, y2) with the y-coordinates adjusted to be measured from the top of the page.
    """
    x1, y2, x2, y1 = rect
    y1 = height - y1
    y2 = height - y2
    return (x1, y1, x2, y2)


def _is_duplicate_char(char1: LTChar, char2: LTChar, threshold: float) -> bool:
    """Detect if two characters are duplicates caused by fake bold rendering.

    Some PDF generators create bold text by rendering the same character twice at slightly
    offset positions. This function detects such duplicates by checking if two characters
    have the same text content and overlapping bounding boxes.

    Key insight: Fake-bold duplicates OVERLAP significantly, while legitimate consecutive
    identical letters (like "ll" in "skills") are ADJACENT with minimal/no overlap.

    Args:
        char1: First LTChar object.
        char2: Second LTChar object.
        threshold: Maximum pixel distance to consider as duplicate.

    Returns:
        True if char2 appears to be a duplicate of char1.
    """
    # Must be the same character
    if char1.get_text() != char2.get_text():
        return False

    # Calculate horizontal and vertical distances between character origins
    x_diff = abs(char1.x0 - char2.x0)
    y_diff = abs(char1.y0 - char2.y0)

    # Characters must be very close in position
    if x_diff >= threshold or y_diff >= threshold:
        return False

    # Additional check: Calculate bounding box overlap to distinguish
    # fake-bold (high overlap) from legitimate doubles (low/no overlap)

    # Get character widths and heights
    char1_width = char1.x1 - char1.x0
    char2_width = char2.x1 - char2.x0

    # Calculate horizontal overlap
    overlap_x_start = max(char1.x0, char2.x0)
    overlap_x_end = min(char1.x1, char2.x1)
    horizontal_overlap = max(0, overlap_x_end - overlap_x_start)

    # Calculate overlap percentage relative to character width
    avg_width = (char1_width + char2_width) / 2
    overlap_ratio = horizontal_overlap / avg_width if avg_width > 0 else 0

    # Fake-bold duplicates typically have >70% overlap
    # Legitimate consecutive letters have <30% overlap (or none)
    # Use configurable threshold (default 50%) to be conservative
    overlap_ratio_threshold = env_config.PDF_CHAR_OVERLAP_RATIO_THRESHOLD
    return overlap_ratio > overlap_ratio_threshold


def deduplicate_chars_in_text_line(text_line: LTTextLine, threshold: float) -> str:
    """Extract text from an LTTextLine with duplicate characters removed.

    Some PDFs create bold text by rendering each character twice at slightly offset
    positions. This function removes such duplicates by keeping only the first instance
    when two identical characters appear at nearly the same position.

    Args:
        text_line: An LTTextLine object containing characters to extract.
        threshold: Maximum pixel distance to consider characters as duplicates.
                   Set to 0 to disable deduplication.

    Returns:
        The extracted text with duplicate characters removed.
    """
    if threshold <= 0:
        return text_line.get_text()

    # Build deduplicated text while preserving non-LTChar items (like LTAnno for spaces)
    result_parts: List[str] = []
    last_ltchar: Optional[LTChar] = None

    for item in text_line:
        if isinstance(item, LTChar):
            # Check if this is a duplicate of the last LTChar
            if last_ltchar is not None and _is_duplicate_char(last_ltchar, item, threshold):
                # Skip this duplicate character
                continue
            last_ltchar = item
            result_parts.append(item.get_text())
        else:
            # Non-LTChar items (e.g., LTAnno for spaces) - keep as-is
            if hasattr(item, "get_text"):
                result_parts.append(item.get_text())

    return "".join(result_parts)


def get_text_with_deduplication(
    text_obj: Union[LTTextLine, LTContainer, LTItem],
    threshold: float,
) -> str:
    """Get text from a text object with optional character deduplication.

    This is the main entry point for extracting text with fake-bold deduplication.
    It handles LTTextLine objects and recursively processes containers.

    Args:
        text_obj: An LTTextLine, LTContainer, or other LTItem object.
        threshold: Maximum pixel distance to consider characters as duplicates.
                   Set to 0 to disable deduplication.

    Returns:
        The extracted text with duplicate characters removed.
    """
    if isinstance(text_obj, LTTextLine):
        return deduplicate_chars_in_text_line(text_obj, threshold)
    elif isinstance(text_obj, LTContainer):
        parts: List[str] = []
        for child in text_obj:
            if isinstance(child, LTTextLine):
                parts.append(deduplicate_chars_in_text_line(child, threshold))
            elif hasattr(child, "get_text"):
                parts.append(child.get_text())
        return "".join(parts)
    elif hasattr(text_obj, "get_text"):
        return text_obj.get_text()
    return ""


@requires_dependencies(["pikepdf", "pypdf"])
def open_pdfminer_pages_generator(
    fp: BinaryIO, password: Optional[str] = None, pdfminer_config: Optional[PDFMinerConfig] = None
):
    """Open PDF pages using PDFMiner, handling and repairing invalid dictionary constructs."""

    import pikepdf

    from unstructured.partition.pdf_image.pypdf_utils import get_page_data

    device, interpreter = init_pdfminer(pdfminer_config=pdfminer_config)
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_file_path = os.path.join(tmp_dir_path, "tmp_file")
        try:
            pages = PDFPage.get_pages(fp, password=password or "")
            # Detect invalid dictionary construct for entire PDF
            for i, page in enumerate(pages):
                try:
                    # Detect invalid dictionary construct for one page
                    interpreter.process_page(page)
                    page_layout = device.get_result()
                except PSSyntaxError:
                    logger.info("Detected invalid dictionary construct for PDFminer")
                    logger.info(f"Repairing the PDF page {i + 1} ...")
                    # find the error page from binary data fp
                    error_page_data = get_page_data(fp, page_number=i)
                    # repair the error page with pikepdf
                    with pikepdf.Pdf.open(error_page_data) as pdf:
                        pdf.save(tmp_file_path)
                    page = next(PDFPage.get_pages(open(tmp_file_path, "rb")))  # noqa: SIM115
                    interpreter.process_page(page)
                    page_layout = device.get_result()
                yield page, page_layout
        except PSSyntaxError:
            logger.info("Detected invalid dictionary construct for PDFminer")
            logger.info("Repairing the PDF document ...")
            # repair the entire doc with pikepdf
            with pikepdf.Pdf.open(fp) as pdf:
                pdf.save(tmp_file_path)
            pages = PDFPage.get_pages(open(tmp_file_path, "rb"))  # noqa: SIM115
            for page in pages:
                interpreter.process_page(page)
                page_layout = device.get_result()
                yield page, page_layout
