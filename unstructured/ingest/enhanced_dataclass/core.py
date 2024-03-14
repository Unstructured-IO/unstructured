import _thread
import copy
import functools
from dataclasses import fields

from dataclasses_json.core import (
    Collection,
    Enum,
    Mapping,
    _encode_overrides,
    _handle_undefined_parameters_safe,
    _user_overrides_or_exts,
    is_dataclass,
)


def _recursive_repr(user_function):
    # Copied from dataclasses as this method isn't exposed for importing
    repr_running = set()

    @functools.wraps(user_function)
    def wrapper(self):
        key = id(self), _thread.get_ident()
        if key in repr_running:
            return "..."
        repr_running.add(key)
        try:
            result = user_function(self)
        finally:
            repr_running.discard(key)
        return result

    return wrapper


def _asdict(
    obj,
    encode_json=False,
    redact_sensitive=False,
    redacted_text="***REDACTED***",
    apply_name_overload: bool = True,
):
    """
    A re-implementation of `asdict` (based on the original in the `dataclasses`
    source) to support arbitrary Collection and Mapping types.
    """
    if is_dataclass(obj):
        result = []
        overrides = _user_overrides_or_exts(obj)
        for field in fields(obj):
            if overrides[field.name].encoder:
                value = getattr(obj, field.name)
            else:
                value = _asdict(
                    getattr(obj, field.name),
                    encode_json=encode_json,
                    redact_sensitive=redact_sensitive,
                    redacted_text=redacted_text,
                    apply_name_overload=apply_name_overload,
                )
            if getattr(field, "sensitive", False) and redact_sensitive and value:
                value = redacted_text
            if getattr(field, "overload_name", None) and apply_name_overload:
                overload_name = getattr(field, "overload_name")
                result.append((overload_name, value))
            else:
                result.append((field.name, value))

        result = _handle_undefined_parameters_safe(cls=obj, kvs=dict(result), usage="to")
        return _encode_overrides(
            dict(result), _user_overrides_or_exts(obj), encode_json=encode_json
        )
    elif isinstance(obj, Mapping):
        return {
            _asdict(
                k,
                encode_json=encode_json,
                redact_sensitive=redact_sensitive,
                redacted_text=redacted_text,
            ): _asdict(
                v,
                encode_json=encode_json,
                redact_sensitive=redact_sensitive,
                redacted_text=redacted_text,
            )
            for k, v in obj.items()
        }
    elif isinstance(obj, Collection) and not isinstance(obj, (str, bytes, Enum)):
        return [
            _asdict(
                v,
                encode_json=encode_json,
                redact_sensitive=redact_sensitive,
                redacted_text=redacted_text,
            )
            for v in obj
        ]
    else:
        return copy.deepcopy(obj)
