import json
import typing as t
from pathlib import Path

from dataclasses_json import DataClassJsonMixin
from dataclasses_json.core import _ExtendedEncoder


class IngestDocJsonMixin(DataClassJsonMixin):
    properties_to_serialize = [
        "base_filename",
        "date_created",
        "date_modified",
        "date_processed",
        "exists",
        "filename",
        "_output_filename",
        "record_locator",
        "source_url",
        "version",
    ]

    def to_json(
        self,
        *,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: t.Optional[t.Union[int, str]] = None,
        separators: t.Optional[t.Tuple[str, str]] = None,
        default: t.Optional[t.Callable] = None,
        sort_keys: bool = False,
        **kw,
    ) -> str:
        as_dict = self.to_dict(encode_json=False)
        for prop in self.properties_to_serialize:
            val = getattr(self, prop)
            if isinstance(val, Path):
                val = str(val)
            as_dict[prop] = val
        return json.dumps(
            as_dict,
            cls=_ExtendedEncoder,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )
