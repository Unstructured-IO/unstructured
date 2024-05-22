from __future__ import annotations

import json
from dataclasses import InitVar, fields
from typing import Any, Callable, Optional, Type, TypeVar, Union

import dataclasses_json.core as dataclasses_json_core
from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.enhanced_dataclass.core import _asdict

A = TypeVar("A", bound="EnhancedDataClassJsonMixin")

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
    """A mixin class extending DataClassJsonMixin.

    This class extends the functionality of DataClassJsonMixin to provide enhanced functionality
    for JSON serialization and deserialization. It introduces options for redacting sensitive
    information, custom encoding, and more advanced schema handling.

    Attributes:
        N/A (No additional attributes)

    Methods:
        to_json: Serialize the object to JSON format with customizable options.
        from_dict: Deserialize a dictionary into an object of this class.
        to_dict: Convert the object to a dictionary with customizable options.
        schema: Generate a schema for validating and parsing JSON data based on this class.
    """

    @classmethod
    def check_init_var(cls):
        ann = cls.__dict__.get("__annotations__", {})
        init_vars = {k: v for k, v in ann.items() if isinstance(v, InitVar)}
        if init_vars:
            raise TypeError(
                "Class {} has the following fields defined with an InitVar which "
                "cannot be used with EnhancedDataClassJsonMixin: {}".format(
                    cls.__name__, ", ".join(init_vars.keys())
                )
            )

    def to_json(
        self,
        *,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: Optional[Union[int, str]] = None,
        separators: Optional[tuple[str, str]] = None,
        default: Optional[Callable[..., Any]] = None,
        sort_keys: bool = False,
        redact_sensitive: bool = False,
        redacted_text: str = "***REDACTED***",
        apply_name_overload: bool = True,
        **kw: Any,
    ) -> str:
        self.check_init_var()
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
            **kw,
        )

    @classmethod
    def from_dict(
        cls: Type[A],
        kvs: dataclasses_json_core.Json,
        *,
        infer_missing=False,
        apply_name_overload=False,
    ) -> A:
        cls.check_init_var()
        return dataclasses_json_core._decode_dataclass(cls, kvs, infer_missing)

    def to_dict(
        self,
        encode_json: bool = False,
        redact_sensitive: bool = False,
        redacted_text: str = "***REDACTED***",
        apply_name_overload: bool = True,
    ) -> dict[str, dataclasses_json_core.Json]:
        self.check_init_var()
        return _asdict(
            self,
            encode_json=encode_json,
            redact_sensitive=redact_sensitive,
            redacted_text=redacted_text,
            apply_name_overload=apply_name_overload,
        )
