import codecs
import warnings
from typing import IO, Optional, Tuple, Union

from charset_normalizer import detect, from_bytes

from unstructured.errors import UnprocessableEntityError
from unstructured.partition.common.common import convert_to_bytes

ENCODE_REC_THRESHOLD = 0.8


class EncodingDetectionWarning(UserWarning):
    """A legacy or BOM-less UTF-16/32 encoding was inferred rather than specified.

    Automatic detection is heuristic, even at high confidence. Callers that prefer
    an exception to potentially incorrect text can promote this warning to an error
    using Python's warnings filters. Pass the source encoding explicitly to avoid
    statistical detection. UTF-8/ASCII and Unicode BOMs do not produce this warning.
    """


# popular encodings from https://en.wikipedia.org/wiki/Popularity_of_text_encodings
# This list is not an exhaustive list of valid encodings or a detection allowlist.
COMMON_ENCODINGS = [
    "utf_8",
    "iso_8859_1",
    "iso_8859_6",
    "iso_8859_8",
    "ascii",
    "big5",
    "utf_16",
    "utf_16_be",
    "utf_16_le",
    "utf_32",
    "utf_32_be",
    "utf_32_le",
    "euc_jis_2004",
    "euc_jisx0213",
    "euc_jp",
    "euc_kr",
    "gb18030",
    "shift_jis",
    "shift_jis_2004",
    "shift_jisx0213",
]


def format_encoding_str(encoding: str) -> str:
    """Format input encoding string (e.g., `utf-8`, `iso-8859-1`, etc).
    Parameters
    ----------
    encoding
        The encoding string to be formatted (e.g., `UTF-8`, `utf_8`, `ISO-8859-1`, `iso_8859_1`,
        etc).
    """
    formatted_encoding = encoding.lower().replace("_", "-")

    # Special case for Arabic and Hebrew charsets with directional annotations
    annotated_encodings = ["iso-8859-6-i", "iso-8859-6-e", "iso-8859-8-i", "iso-8859-8-e"]
    if formatted_encoding in annotated_encodings:
        formatted_encoding = formatted_encoding[:-2]  # remove the annotation

    return formatted_encoding


def validate_encoding(encoding: str) -> bool:
    """Checks if an encoding string is valid. Helps to avoid errors in cases where
    invalid encodings are extracted from malformed documents."""
    for common_encoding in COMMON_ENCODINGS:
        if format_encoding_str(common_encoding) == format_encoding_str(encoding):
            return True
    return False


def _decode(byte_data: bytes, encoding: str, final: bool) -> str:
    """Decode strictly. With `final=False`, an incomplete trailing sequence is not an error."""
    if final:
        return byte_data.decode(encoding)
    return codecs.getincrementaldecoder(encoding)().decode(byte_data, final=False)


def detect_file_encoding(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    *,
    final: bool = True,
) -> Tuple[str, str]:
    """Decode bytes using a Unicode BOM, strict UTF-8, or best-effort character-set detection.

    A successful decode is not evidence that a guessed encoding is correct.
    Emit EncodingDetectionWarning for statistical legacy/BOM-less UTF-16/32
    detection, so applications can either retain best-effort behavior or reject it.
    UTF-8/ASCII is the default text convention, not a proof of the source encoding.

    Pass `final=False` when the bytes are only a prefix of a longer document. A multi-byte
    sequence cut off at the end of the prefix is then left out instead of failing the decode.
    Every other undecodable byte still fails.
    """
    if filename:
        with open(filename, "rb") as f:
            byte_data = f.read()
    elif file is not None:
        byte_data = convert_to_bytes(file)
    else:
        raise FileNotFoundError("No filename nor file were specified")

    # UTF-32 must precede UTF-16: their little-endian BOMs share a prefix.
    bom_encoding = next(
        (
            encoding
            for bom, encoding in (
                (codecs.BOM_UTF32_LE, "utf-32"),
                (codecs.BOM_UTF32_BE, "utf-32"),
                (codecs.BOM_UTF8, "utf-8-sig"),
                (codecs.BOM_UTF16_LE, "utf-16"),
                (codecs.BOM_UTF16_BE, "utf-16"),
            )
            if byte_data.startswith(bom)
        ),
        None,
    )
    encoding = bom_encoding
    # -- Pure ASCII keeps its detected `ascii` label. NUL is excluded because BOM-less UTF-16/32
    # -- pads ASCII characters with NUL bytes, which UTF-8 also accepts.
    if encoding is None and not byte_data.isascii() and b"\x00" not in byte_data:
        # Valid UTF-8 is structurally unlikely by accident, while permissive single-byte
        # codecs accept anything. Detectors can still prefer one at full confidence when
        # the only non-ASCII bytes are a single character such as U+200B or U+00AD.
        try:
            _decode(byte_data, "utf-8", final)
            encoding = "utf-8"
        except UnicodeDecodeError:
            pass
    if encoding is None:
        result = detect(byte_data)
        encoding = result["encoding"]
        confidence = result["confidence"]

        if encoding is None or confidence is None or confidence < ENCODE_REC_THRESHOLD:
            # Latin-1 decodes every byte, so first-success decoding masks errors and
            # makes later codecs unreachable. Rank real candidates without excluding
            # valid encodings such as cp932/cp1254 just because they are uncommon.
            # Disable unconditional fallback matches for likely binary/non-text input.
            best = from_bytes(byte_data, enable_fallback=False).best()
            if best is None:
                raise UnprocessableEntityError(
                    "Unable to determine file encoding. Specify the source encoding with "
                    "encoding=, or check whether the file is a supported text document."
                ) from None
            encoding = best.encoding

    # Do not expose a UnicodeError's input payload in the public exception.
    try:
        file_text = _decode(byte_data, encoding, final)
        canonical_encoding = codecs.lookup(encoding).name
    except (UnicodeError, LookupError):
        raise UnprocessableEntityError(
            f"File encoding detection failed: detected '{encoding}' but decode failed. "
            "Specify the source encoding with encoding=, or check the file contents."
        ) from None

    if bom_encoding is None and canonical_encoding not in {"ascii", "utf-8", "utf-8-sig"}:
        warnings.warn(
            f"The file encoding was inferred as '{encoding}'. Automatic detection may be "
            "ambiguous and can produce incorrect text. Pass encoding= to specify the "
            "source encoding.",
            EncodingDetectionWarning,
            stacklevel=2,
        )

    formatted_encoding = format_encoding_str(encoding)

    return formatted_encoding, file_text


def read_txt_file(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    encoding: Optional[str] = None,
) -> Tuple[str, str]:
    """Extracts document metadata from a plain text document."""
    if filename:
        if encoding:
            formatted_encoding = format_encoding_str(encoding)
            with open(filename, encoding=formatted_encoding) as f:
                try:
                    file_text = f.read()
                except (UnicodeDecodeError, UnicodeError) as error:
                    raise error
        else:
            formatted_encoding, file_text = detect_file_encoding(filename)
    elif file is not None:
        if encoding:
            formatted_encoding = format_encoding_str(encoding)
            try:
                file_content = file if isinstance(file, bytes) else file.read()
                if isinstance(file_content, bytes):
                    file_text = file_content.decode(formatted_encoding)
                else:
                    file_text = file_content
            except (UnicodeDecodeError, UnicodeError) as error:
                raise error
        else:
            formatted_encoding, file_text = detect_file_encoding(file=file)
    else:
        raise FileNotFoundError("No filename was specified")

    return formatted_encoding, file_text
