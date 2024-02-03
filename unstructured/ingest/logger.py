import ast
import json
import logging
import typing as t

logger = logging.getLogger("unstructured.ingest")


def default_is_data_sensitive(k: str, v: t.Any) -> bool:
    sensitive_fields = [
        "account_name",
        "client_id",
    ]
    sensitive_triggers = ["key", "cred", "token", "password", "oauth", "secret"]
    return (
        v
        and any([s in k.lower() for s in sensitive_triggers])  # noqa: C419
        or k.lower() in sensitive_fields
    )


def hide_sensitive_fields(
    data: dict, is_sensitive_fn: t.Callable[[str, t.Any], bool] = default_is_data_sensitive
) -> dict:
    """
    Will recursively look through every k, v pair in this dict and any nested ones and run
    is_sensitive_fn to dynamically redact the value of the k, v pair. Will also check if
    any string value can be parsed as valid json and process that dict as well and replace
    the original string with the json.dumps() version of the redacted dict.
    """
    new_data = data.copy()
    for k, v in new_data.items():
        if is_sensitive_fn(k, v):
            new_data[k] = "*******"
        if isinstance(v, dict):
            new_data[k] = hide_sensitive_fields(v)
        if isinstance(v, str):
            # Need to take into account strings generated via json.dumps() or simply printing a dict
            try:
                json_data = json.loads(v)
                if isinstance(json_data, dict):
                    updated_data = hide_sensitive_fields(json_data)
                    new_data[k] = json.dumps(updated_data)
            except json.JSONDecodeError:
                pass

    return new_data


def redact_jsons(s: str) -> str:
    """
    Takes in a generic string and pulls out all valid json content. Leverages
    hide_sensitive_fields() to redact any sensitive information and replaces the
    original json with the new redacted format. There can be any number of valid
    jsons in a generic string and this will work. Having extra '{' without a
    closing '}' will cause this to break though. i.e '{ text, {"a": 3}'.

    """
    chars = list(s)
    if "{" not in chars:
        return s
    i = 0
    jsons = []
    i = 0
    while i < len(chars):
        char = chars[i]
        if char == "{":
            stack = [char]
            current = [char]
            while len(stack) != 0 and i < len(chars):
                i += 1
                char = chars[i]
                current.append(char)
                if char == "{":
                    stack.append(char)
                if char == "}":
                    stack.pop(-1)
            jsons.append("".join(current))
            continue
        i += 1
    for j in jsons:
        try:
            formatted_j = json.dumps(json.loads(j))
        except json.JSONDecodeError:
            formatted_j = json.dumps(ast.literal_eval(j))
        hidden_j = json.dumps(hide_sensitive_fields(json.loads(formatted_j)))
        s = s.replace(j, hidden_j)
    return s


class SensitiveFormatter(logging.Formatter):
    def format(self, record):
        s = super().format(record=record)
        return redact_jsons(s)


def ingest_log_streaming_init(level: int) -> None:
    handler = logging.StreamHandler()
    handler.name = "ingest_log_handler"
    formatter = SensitiveFormatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)

    # Only want to add the handler once
    if "ingest_log_handler" not in [h.name for h in logger.handlers]:
        logger.addHandler(handler)

    logger.setLevel(level)


def make_default_logger(level: int) -> logging.Logger:
    """Return a custom logger."""
    logger = logging.getLogger("unstructured.ingest")
    handler = logging.StreamHandler()
    handler.name = "ingest_log_handler"
    formatter = SensitiveFormatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger
