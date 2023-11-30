import json
import typing as t
from dataclasses import fields

from dataclasses_json import DataClassJsonMixin
from dataclasses_json.core import Json, _decode_dataclass, _ExtendedEncoder

from unstructured.ingest.enhanced_dataclass.core import _asdict

A = t.TypeVar("A", bound="EnhancedDataClassJsonMixin")


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
        redact_sensitive=False,
        redacted_text="***REDACTED***",
        **kw
    ) -> str:
        return json.dumps(
            self.to_dict(
                encode_json=False,
                redact_sensitive=redact_sensitive,
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

    @classmethod
    def from_dict(
        cls: t.Type[A], kvs: Json, *, infer_missing=False, apply_name_overload: bool = True
    ) -> A:
        dataclass_fields = fields(cls)
        for f in [field for field in dataclass_fields if hasattr(field, "overload_name")]:
            field_name = f.name
            overload_name = getattr(f, "overload_name")
            if isinstance(kvs, dict) and overload_name in kvs and apply_name_overload:
                kvs[field_name] = kvs.pop(overload_name)

        return _decode_dataclass(cls, kvs, infer_missing)

    def to_dict(
        self,
        encode_json=False,
        redact_sensitive=False,
        redacted_text="***REDACTED***",
        apply_name_overload: bool = True,
    ) -> t.Dict[str, Json]:
        return _asdict(
            self,
            encode_json=encode_json,
            redact_sensitive=redact_sensitive,
            redacted_text=redacted_text,
            apply_name_overload=apply_name_overload,
        )
