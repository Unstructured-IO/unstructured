from typing import IO, Optional, Tuple, Union

import chardet

from unstructured.partition.common import convert_to_bytes

ENCODE_REC_THRESHOLD = 0.8

# popular encodings from https://en.wikipedia.org/wiki/Popularity_of_text_encodings
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


def detect_file_encoding(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
) -> Tuple[str, str]:
    if filename:
        with open(filename, "rb") as f:
            byte_data = f.read()
    elif file:
        byte_data = convert_to_bytes(file)
    else:
        raise FileNotFoundError("No filename nor file were specified")

    result = chardet.detect(byte_data)
    encoding = result["encoding"]
    confidence = result["confidence"]

    if encoding is None or confidence < ENCODE_REC_THRESHOLD:
        # Encoding detection failed, fallback to predefined encodings
        for enc in COMMON_ENCODINGS:
            try:
                if filename:
                    with open(filename, encoding=enc) as f:
                        file_text = f.read()
                else:
                    file_text = byte_data.decode(enc)
                encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            raise UnicodeDecodeError(
                "Unable to determine the encoding of the file or match it with any "
                "of the specified encodings.",
                byte_data,
                0,
                len(byte_data),
                "Invalid encoding",
            )

    else:
        file_text = byte_data.decode(encoding)

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
    elif file:
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
