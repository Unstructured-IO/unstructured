from datetime import datetime
from typing import Union

from dateutil import parser


def parse_datetime(date_value: Union[int, str, float, datetime]) -> datetime:
    if isinstance(date_value, datetime):
        return date_value
    elif isinstance(date_value, float):
        return datetime.fromtimestamp(date_value)
    elif isinstance(date_value, int):
        return datetime.fromtimestamp(date_value / 1000)

    try:
        timestamp = float(date_value)
        return datetime.fromtimestamp(timestamp)
    except ValueError:
        return parser.parse(date_value)
