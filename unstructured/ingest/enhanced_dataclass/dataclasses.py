import typing as t
from dataclasses import MISSING, Field

from unstructured.ingest.enhanced_dataclass.core import _recursive_repr


class EnhancedField(Field):
    def __init__(self, *args, sensitive=False, overload_name: t.Optional[str] = None):
        super().__init__(*args)
        self.sensitive = sensitive
        self.overload_name = overload_name

    @_recursive_repr
    def __repr__(self):
        # Support for kw_only added in 3.10, to support as low as 3.8, need to dynamically map
        fields_array = [
            f"name={self.name!r}",
            f"type={self.type!r}",
            f"default={self.default!r}",
            f"default_factory={self.default_factory!r}",
            f"init={self.init!r}",
            f"repr={self.repr!r}",
            f"hash={self.hash!r}",
            f"compare={self.compare!r}",
            f"metadata={self.metadata!r}",
            f"sensitive={self.sensitive!r}",
            f"overload_name={self.overload_name!r}",
            f"_field_type={self._field_type}",
        ]
        if kw_only := getattr(self, "kw_only", None):
            fields_array.append(f"kw_only={kw_only!r}")
        return "Field({})".format(",".join(fields_array))


def enhanced_field(
    *,
    default=MISSING,
    default_factory=MISSING,
    init: bool = True,
    repr: bool = True,
    hash=None,
    compare: bool = True,
    metadata=None,
    kw_only=MISSING,
    sensitive: bool = False,
    overload_name: t.Optional[str] = None,
):
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("cannot specify both default and default_factory")
    args = [default, default_factory, init, repr, hash, compare, metadata]
    # Support for kw_only added in 3.10, to support as low as 3.8, need to dynamically map
    if "kw_only" in EnhancedField.__slots__:
        args.append(kw_only)
    return EnhancedField(*args, sensitive=sensitive, overload_name=overload_name)
