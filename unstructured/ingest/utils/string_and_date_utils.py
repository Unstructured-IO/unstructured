import json
import typing as t
from datetime import datetime

from dateutil import parser


def json_to_dict(json_string: str) -> t.Union[str, t.Dict[str, t.Any]]:
    """Helper function attempts to deserialize json string to a dictionary."""
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        # Not neccessary an error if it is a path or malformed json
        pass
    try:
        # This is common when single quotes are used instead of double quotes
        return json.loads(json_string.replace("'", '"'))
    except json.JSONDecodeError:
        # Not neccessary an error if it is a path
        pass
    return json_string


def ensure_isoformat_datetime(timestamp: t.Union[datetime, str]) -> str:
    """
    Ensures that the input value is converted to an ISO format datetime string.
    Handles both datetime objects and strings.
    """
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    elif isinstance(timestamp, str):
        try:
            # Parse the datetime string in various formats
            dt = parser.parse(timestamp)
            return dt.isoformat()
        except ValueError as e:
            raise ValueError(f"String '{timestamp}' could not be parsed as a datetime.") from e
    else:
        raise TypeError(f"Expected input type datetime or str, but got {type(timestamp)}.")
