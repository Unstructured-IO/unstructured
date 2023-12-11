import json
import typing as t
from dataclasses import fields

import dataclasses_json.core as dataclasses_json_core
from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.enhanced_dataclass.core import _asdict

A = t.TypeVar("A", bound="EnhancedDataClassJsonMixin")

# Monkey-patch _decode_dataclass class to support name override
og_decode_dataclass = dataclasses_json_core._decode_dataclass


def custom_decode_dataclass(cls, kvs, infer_missing):
    dataclass_fields = fields(cls)
    for f in [
        field
        for field in dataclass_fields
        if hasattr(field, "overload_name") and getattr(field, "overload_name", None)
    ]:
        field_name = f.name
        overload_name = getattr(f, "overload_name")
        if isinstance(kvs, dict) and overload_name in kvs:
            kvs[field_name] = kvs.pop(overload_name)
    return og_decode_dataclass(cls, kvs, infer_missing)


dataclasses_json_core._decode_dataclass = custom_decode_dataclass


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
        apply_name_overload: bool = True,
        **kw
    ) -> str:
        return json.dumps(
            self.to_dict(
                encode_json=False,
                redact_sensitive=redact_sensitive,
                redacted_text=redacted_text,
                apply_name_overload=apply_name_overload,
            ),
            cls=dataclasses_json_core._ExtendedEncoder,
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
        cls: t.Type[A],
        kvs: dataclasses_json_core.Json,
        *,
        infer_missing=False,
        apply_name_overload=False
    ) -> A:
        return dataclasses_json_core._decode_dataclass(cls, kvs, infer_missing)

    def to_dict(
        self,
        encode_json=False,
        redact_sensitive=False,
        redacted_text="***REDACTED***",
        apply_name_overload: bool = True,
    ) -> t.Dict[str, dataclasses_json_core.Json]:
        return _asdict(
            self,
            encode_json=encode_json,
            redact_sensitive=redact_sensitive,
            redacted_text=redacted_text,
            apply_name_overload=apply_name_overload,
        )
