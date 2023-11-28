import ast
import json
import logging

logger = logging.getLogger("unstructured.ingest")


def hide_sensitive_fields(data: dict) -> dict:
    sensitive_fields = [
        "account_name",
        "client_id",
    ]
    sensitive_triggers = ["key", "cred", "token"]
    new_data = data.copy()
    for k, v in new_data.items():
        if (
            v
            and any([s in k.lower() for s in sensitive_triggers])  # noqa: C419
            or k.lower() in sensitive_fields
        ):
            new_data[k] = "*******"
        if isinstance(v, dict):
            new_data[k] = hide_sensitive_fields(v)
        if isinstance(v, str):
            try:
                json_data = json.loads(v)
                if isinstance(json_data, dict):
                    updated_data = hide_sensitive_fields(json_data)
                    new_data[k] = json.dumps(updated_data)
            except json.JSONDecodeError:
                pass

    return new_data


def extract_json(s: str) -> str:
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
        return extract_json(s)


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
