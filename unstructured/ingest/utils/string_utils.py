import json
import typing as t


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
