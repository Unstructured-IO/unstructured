from typing import IO, Optional, Tuple, Union

import chardet

ENCODE_REC_THRESHOLD = 0.5

# popular encodings from https://en.wikipedia.org/wiki/Popularity_of_text_encodings
COMMON_ENCODINGS = [
    "utf_8",
    "iso_8859_1",
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


def detect_file_encoding(
    filename: str = "",
    file: Optional[Union[bytes, IO]] = None,
) -> Tuple[str, str]:
    if filename:
        with open(filename, "rb") as f:
            byte_data = f.read()
    elif file:
        if isinstance(file, bytes):
            byte_data = file
        else:
            if not hasattr(file, "mode") or "b" in file.mode:
                byte_data = file.read()
            else:
                with open(file.name, "rb") as f:
                    byte_data = f.read()
    else:
        raise FileNotFoundError("No filename nor file were specified")

    result = chardet.detect(byte_data)
    encoding = result["encoding"]
    confidence = result["confidence"]

    if encoding is None or confidence < ENCODE_REC_THRESHOLD:
        # Encoding detection failed, fallback to predefined encodings
        for enc in COMMON_ENCODINGS:
            try:
                with open(filename, encoding=enc) as f:
                    file_text = f.read()
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

    return encoding, file_text


def read_txt_file(
    filename: str = "",
    file: Optional[Union[bytes, IO]] = None,
    encoding: Optional[str] = None,
) -> Tuple[str, str]:
    """Extracts document metadata from a plain text document."""
    if filename:
        if encoding:
            with open(filename, encoding=encoding) as f:
                try:
                    file_text = f.read()
                except (UnicodeDecodeError, UnicodeError) as error:
                    raise error
        else:
            encoding, file_text = detect_file_encoding(filename)
    elif file:
        if encoding:
            try:
                file_content = file if isinstance(file, bytes) else file.read()
                if isinstance(file_content, bytes):
                    file_text = file_content.decode(encoding)
                else:
                    file_text = file_content
            except (UnicodeDecodeError, UnicodeError) as error:
                raise error
        else:
            encoding, file_text = detect_file_encoding(file=file)
    else:
        raise FileNotFoundError("No filename was specified")

    return encoding, file_text
