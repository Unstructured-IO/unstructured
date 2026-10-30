"""
Adds support for working with newline-delimited JSON (ndjson) files. This format is useful for
streaming json content that would otherwise not be possible using raw JSON files.
"""

import json
import re
from typing import IO, Any

# NOTE(tanishqbaweja): the line breaks `str.splitlines()` splits on, except U+0085, U+2028 and
# U+2029. JSON allows those three unescaped inside a string, so they don't end a record. The
# others are control characters, which JSON doesn't allow unescaped inside a string.
_LINE_BREAK = re.compile(r"\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e]")


def dumps(obj: list[dict[str, Any]], **kwargs) -> str:
    """
    Converts the list of dictionaries into string representation

    Args:
        obj (list[dict[str, Any]]): List of dictionaries to convert
        **kwargs: Additional keyword arguments to pass to json.dumps

    Returns:
        str: string representation of the list of dictionaries
    """
    return "\n".join(json.dumps(each, **kwargs) for each in obj)


def dump(obj: list[dict[str, Any]], fp: IO, **kwargs) -> None:
    """
    Writes the list of dictionaries to a newline-delimited file

    Args:
        obj (list[dict[str, Any]]): List of dictionaries to convert
        fp (IO): File pointer to write the string representation to
        **kwargs: Additional keyword arguments to pass to json.dumps

    Returns:
        None
    """
    # Indent breaks ndjson formatting
    kwargs["indent"] = None
    text = dumps(obj, **kwargs)
    fp.write(text)


def split_lines(text: str) -> list[str]:
    """Split newline-delimited JSON `text` into its lines.

    Like `str.splitlines()`, except that a U+0085, U+2028 or U+2029 inside a JSON string doesn't
    end the line.

    Args:
        text (str): Newline-delimited JSON

    Returns:
        list[str]: The lines of `text`, without their line breaks
    """
    lines = _LINE_BREAK.split(text)
    # -- like `str.splitlines()`, a final line break doesn't start another line --
    if lines[-1] == "":
        lines.pop()
    return lines


def loads(s: str, **kwargs) -> list[dict[str, Any]]:
    """
    Converts the raw string into a list of dictionaries

    Args:
        s (str): Raw string to convert
        **kwargs: Additional keyword arguments to pass to json.loads

    Returns:
        list[dict[str, Any]]: List of dictionaries parsed from the input string
    """
    return [json.loads(line, **kwargs) for line in split_lines(s)]


def load(fp: IO, **kwargs) -> list[dict[str, Any]]:
    """
    Converts the contents of the file into a list of dictionaries

    Args:
        fp (IO): File pointer to read the string representation from
        **kwargs: Additional keyword arguments to pass to json.loads

    Returns:
        list[dict[str, Any]]: List of dictionaries parsed from the file
    """
    return loads(fp.read(), **kwargs)
