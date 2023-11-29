from dataclasses import MISSING, Field

from unstructured.ingest.enhanced_dataclass.core import _recursive_repr


class EnhancedField(Field):
    __slots__ = (
        "name",
        "type",
        "default",
        "default_factory",
        "repr",
        "hash",
        "init",
        "compare",
        "metadata",
        "kw_only",
        "sensitive",
        "_field_type",  # Private: not to be used by user code.
    )

    def __init__(self, *args, sensitive=False):
        super().__init__(*args)
        self.sensitive = sensitive

    @_recursive_repr
    def __repr__(self):
        return (
            "Field("
            f"name={self.name!r},"
            f"type={self.type!r},"
            f"default={self.default!r},"
            f"default_factory={self.default_factory!r},"
            f"init={self.init!r},"
            f"repr={self.repr!r},"
            f"hash={self.hash!r},"
            f"compare={self.compare!r},"
            f"metadata={self.metadata!r},"
            f"kw_only={self.kw_only!r},"
            f"sensitive={self.sensitive!r},"
            f"_field_type={self._field_type}"
            ")"
        )


def enhanced_field(
    *,
    default=MISSING,
    default_factory=MISSING,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    metadata=None,
    kw_only=MISSING,
    sensitive=False,
):
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return EnhancedField(
        default, default_factory, init, repr, hash, compare, metadata, kw_only, sensitive=sensitive
    )
