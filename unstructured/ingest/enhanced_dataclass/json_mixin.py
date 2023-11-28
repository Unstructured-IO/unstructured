import json
import typing as t

from dataclasses_json import DataClassJsonMixin
from dataclasses_json.core import Json, _ExtendedEncoder

from unstructured.ingest.enhanced_dataclass.core import _asdict


class EnhancedDataClassJsonMixin(DataClassJsonMixin):
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
        preserve_sensitive=True,
        redacted_text="***REDACTED***",
        **kw
    ) -> str:
        return json.dumps(
            self.to_dict(
                encode_json=False,
                preserve_sensitive=preserve_sensitive,
                redacted_text=redacted_text,
            ),
            cls=_ExtendedEncoder,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw
        )

    def to_dict(
        self, encode_json=False, preserve_sensitive=True, redacted_text="***REDACTED***"
    ) -> t.Dict[str, Json]:
        return _asdict(
            self,
            encode_json=encode_json,
            preserve_sensitive=preserve_sensitive,
            redacted_text=redacted_text,
        )
