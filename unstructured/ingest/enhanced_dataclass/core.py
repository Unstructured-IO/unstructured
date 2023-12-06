import _thread
import copy
import functools
import warnings
from dataclasses import fields

from dataclasses_json.core import (
    MISSING,
    Collection,
    Enum,
    Mapping,
    _decode_generic,
    _decode_letter_case_overrides,
    _encode_overrides,
    _handle_undefined_parameters_safe,
    _is_new_type,
    _is_optional,
    _is_supported_generic,
    _isinstance_safe,
    _support_extended_types,
    _user_overrides_or_exts,
    get_type_hints,
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
            if getattr(field, "sensitive", False) and redact_sensitive:
                value = redacted_text
            elif overrides[field.name].encoder:
                value = getattr(obj, field.name)
            else:
                value = _asdict(
                    getattr(obj, field.name),
                    encode_json=encode_json,
                    redact_sensitive=redact_sensitive,
                    redacted_text=redacted_text,
                )
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


def _decode_dataclass(cls, kvs, infer_missing, apply_name_overload: bool = True):
    """
    Copy of the _decode_dataclass from dataclasses_json.core with support for name overrides
    """
    if _isinstance_safe(kvs, cls):
        return kvs
    overrides = _user_overrides_or_exts(cls)
    kvs = {} if kvs is None and infer_missing else kvs
    dataclass_fields = fields(cls)
    for f in [field for field in dataclass_fields if hasattr(field, "overload_name")]:
        field_name = f.name
        overload_name = getattr(f, "overload_name")
        if isinstance(kvs, dict) and overload_name in kvs and apply_name_overload:
            kvs[field_name] = kvs.pop(overload_name)
    field_names = [field.name for field in fields(cls)]
    decode_names = _decode_letter_case_overrides(field_names, overrides)
    kvs = {decode_names.get(k, k): v for k, v in kvs.items()}
    missing_fields = {field for field in fields(cls) if field.name not in kvs}

    for field in missing_fields:
        if field.default is not MISSING:
            kvs[field.name] = field.default
        elif field.default_factory is not MISSING:
            kvs[field.name] = field.default_factory()
        elif infer_missing:
            kvs[field.name] = None

    # Perform undefined parameter action
    kvs = _handle_undefined_parameters_safe(cls, kvs, usage="from")

    init_kwargs = {}
    types = get_type_hints(cls)
    for field in fields(cls):
        # The field should be skipped from being added
        # to init_kwargs as it's not intended as a constructor argument.
        if not field.init:
            continue

        try:
            field_value = kvs[field.name]
        except KeyError as e:
            print(f"failed parsing config: {cls}, keys in dict: {kvs.keys()}")
            raise e
        field_type = types[field.name]
        if field_value is None:
            if not _is_optional(field_type):
                warning = (
                    f"value of non-optional type {field.name} detected "
                    f"when decoding {cls.__name__}"
                )
                if infer_missing:
                    warnings.warn(
                        f"Missing {warning} and was defaulted to None by "
                        f"infer_missing=True. "
                        f"Set infer_missing=False (the default) to prevent "
                        f"this behavior.",
                        RuntimeWarning,
                    )
                else:
                    warnings.warn(f"'NoneType' object {warning}.", RuntimeWarning)
            init_kwargs[field.name] = field_value
            continue

        while True:
            if not _is_new_type(field_type):
                break

            field_type = field_type.__supertype__

        if field.name in overrides and overrides[field.name].decoder is not None:
            # FIXME hack
            if field_type is type(field_value):
                init_kwargs[field.name] = field_value
            else:
                init_kwargs[field.name] = overrides[field.name].decoder(field_value)
        elif is_dataclass(field_type):
            # FIXME this is a band-aid to deal with the value already being
            # serialized when handling nested marshmallow schema
            # proper fix is to investigate the marshmallow schema generation
            # code
            if is_dataclass(field_value):
                value = field_value
            else:
                value = _decode_dataclass(field_type, field_value, infer_missing)
            init_kwargs[field.name] = value
        elif _is_supported_generic(field_type) and field_type != str:
            init_kwargs[field.name] = _decode_generic(field_type, field_value, infer_missing)
        else:
            init_kwargs[field.name] = _support_extended_types(field_type, field_value)

    return cls(**init_kwargs)
