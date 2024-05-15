import json
from datetime import datetime
from pathlib import Path


def sterilize_dict(data: dict) -> dict:
    def json_serial(obj):
        if isinstance(obj, Path):
            return obj.as_posix()
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    data_s = json.dumps(data, default=json_serial)
    return json.loads(data_s)
