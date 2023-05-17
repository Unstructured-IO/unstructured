from typing import Optional, Tuple

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


def read_txt_file(
    filename: str = "",
    encoding: Optional[str] = "utf-8",
) -> Tuple[str, str]:
    """Extracts document metadata from a plain text document."""
    if filename:
        with open(filename, encoding=encoding) as f:
            try:
                file_text = f.read()
            except (UnicodeDecodeError, UnicodeError):
                with open(filename, "rb") as f_rb:
                    binary_data = f_rb.read()

                result = chardet.detect(binary_data)
                encoding = result["encoding"]
                confidence = result["confidence"]

                if encoding is None or confidence < ENCODE_REC_THRESHOLD:
                    # Encoding detection failed, fallback to predefined encodings
                    for enc in COMMON_ENCODINGS:
                        try:
                            with open(filename, encoding=enc) as f_retry:
                                file_text = f_retry.read()
                            encoding = enc
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    else:
                        raise UnicodeDecodeError(
                            "Unable to determine the encoding of the file or match it with "
                            "any of the specified encodings.",
                        )

                else:
                    file_text = binary_data.decode(encoding)
    else:
        raise FileNotFoundError("No filename was specified")

    return encoding, file_text
