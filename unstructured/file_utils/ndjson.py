import json


def dumps(obj: list[dict], **kwargs) -> str:
    lines = []
    for each in obj:
        lines.append(json.dumps(each, **kwargs))
    return "\n".join(lines)


def dump(obj, fp, **kwargs):
    # Indent breaks ndjson formatting
    kwargs["indent"] = None
    text = dumps(obj, **kwargs)
    fp.write(text)


def loads(s: str, **kwargs) -> list[dict]:
    lines = s.splitlines()
    return [json.loads(line, **kwargs) for line in lines]


def load(fp, **kwargs) -> list[dict]:
    return loads(fp.read(), **kwargs)
