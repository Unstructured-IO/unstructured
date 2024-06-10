import json
import os.path
import sys
from dataclasses import fields, is_dataclass
from gettext import gettext, ngettext
from pathlib import Path
from typing import Any, ForwardRef, Optional, Type, TypeVar, Union, get_args, get_origin

import click

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.v2.logger import logger


class Dict(click.ParamType):
    name = "dict"

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter] = None,
        ctx: Optional[click.Context] = None,
    ) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            self.fail(
                gettext(
                    "{value} is not a valid json value.",
                ).format(value=value),
                param,
                ctx,
            )


class FileOrJson(click.ParamType):
    name = "file-or-json"

    def __init__(self, allow_raw_str: bool = False):
        self.allow_raw_str = allow_raw_str

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter] = None,
        ctx: Optional[click.Context] = None,
    ) -> Any:
        # check if valid file
        full_path = os.path.abspath(os.path.expanduser(value))
        if os.path.isfile(full_path):
            return str(Path(full_path).resolve())
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                if self.allow_raw_str:
                    return value
        self.fail(
            gettext(
                "{value} is not a valid json string nor an existing filepath.",
            ).format(value=value),
            param,
            ctx,
        )


class DelimitedString(click.ParamType):
    name = "delimited-string"

    def __init__(self, delimiter: str = ",", choices: Optional[list[str]] = None):
        self.choices = choices if choices else []
        self.delimiter = delimiter

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter] = None,
        ctx: Optional[click.Context] = None,
    ) -> Any:
        # In case a list is provided as the default, will not break
        if isinstance(value, list):
            split = [str(v).strip() for v in value]
        else:
            split = [v.strip() for v in value.split(self.delimiter)]
        if not self.choices:
            return split
        choices_str = ", ".join(map(repr, self.choices))
        for s in split:
            if s not in self.choices:
                self.fail(
                    ngettext(
                        "{value!r} is not {choice}.",
                        "{value!r} is not one of {choices}.",
                        len(self.choices),
                    ).format(value=s, choice=choices_str, choices=choices_str),
                    param,
                    ctx,
                )
        return split


EnhancedDataClassJsonMixinT = TypeVar(
    "EnhancedDataClassJsonMixinT", bound=EnhancedDataClassJsonMixin
)


def extract_config(
    flat_data: dict, config: Type[EnhancedDataClassJsonMixinT]
) -> EnhancedDataClassJsonMixinT:
    """
    To be able to extract a nested dataclass from a flat dictionary (as in one coming
    from a click-based options input), the config class is dynamically looked through for
    nested dataclass fields and new nested dictionaries are created to conform to the
    shape the overall class expects when parsing from a dict. During the process, this will create
    copies of the original dictionary to avoid pruning fields but this isn't a
    problem since the `from_dict()` method ignores unneeded values.

    Not handling more complex edge cases for now such as nested types i.e Union[List[List[...]]]
    """

    def conform_dict(inner_d: dict, inner_config: Type[EnhancedDataClassJsonMixinT]):
        # Catch edge cases (i.e. Dict[str, ...]) where underlying type is not a concrete Class,
        # causing 'issubclass() arg 1 must be a class' errors, return False
        def is_subclass(instance, class_type) -> bool:
            try:
                return issubclass(instance, class_type)
            except Exception:
                return False

        dd = inner_d.copy()
        for field in fields(inner_config):
            f_type = field.type
            # typing can be defined using a string, in which case it needs to be resolved
            # to the actual type. following logic is cherry picked from the typing
            # get_type_hints() since type resolution can be expensive, only do it
            # when the type is a string
            if isinstance(f_type, str):
                try:
                    base_globals = sys.modules[inner_config.__module__].__dict__
                    for_ref = ForwardRef(f_type, is_argument=False, is_class=True)
                    f_type = for_ref._evaluate(
                        globalns=base_globals, localns=None, recursive_guard=frozenset()
                    )
                except NameError as e:
                    logger.warning(f"couldn't resolve type {f_type}: {e}")
            # Handle the case where the type of a value if a Union (possibly optional)
            if get_origin(f_type) is Union:
                union_values = get_args(f_type)
                # handle List types
                union_values = [
                    get_args(u)[0] if get_origin(u) is list else u for u in union_values
                ]
                # Ignore injected NoneType when optional
                concrete_union_values = [v for v in union_values if not is_subclass(v, type(None))]
                dataclass_union_values = [v for v in concrete_union_values if is_dataclass(v)]
                non_dataclass_union_values = [
                    v for v in concrete_union_values if not is_dataclass(v)
                ]
                if not dataclass_union_values:
                    continue
                # Check if the key for this field already exists in the dictionary,
                # if so it might map to one of these non dataclass fields and this
                # can't be enforced
                if non_dataclass_union_values and field.name in dd:
                    continue
                if len(dataclass_union_values) > 1:
                    logger.warning(
                        "more than one dataclass type possible for field {}, "
                        "not extracting: {}".format(field.name, ", ".join(dataclass_union_values))
                    )
                    continue
                f_type = dataclass_union_values[0]
            origin = get_origin(f_type)
            if origin:
                f_type = origin
            if is_subclass(f_type, EnhancedDataClassJsonMixin):
                dd[field.name] = conform_dict(inner_d=dd, inner_config=f_type)
        return dd

    adjusted_dict = conform_dict(inner_d=flat_data, inner_config=config)
    return config.from_dict(adjusted_dict, apply_name_overload=False)
