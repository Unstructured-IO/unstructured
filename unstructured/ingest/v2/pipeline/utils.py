import json
from datetime import datetime
from pathlib import Path
from typing import Any


def sterilize_dict(data: dict[str, Any]) -> dict[str, Any]:
    def json_serial(obj: Any) -> str:
        if isinstance(obj, Path):
            return obj.as_posix()
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    data_s = json.dumps(data, default=json_serial)
    return json.loads(data_s)
