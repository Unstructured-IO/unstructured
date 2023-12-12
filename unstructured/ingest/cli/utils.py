import typing as t
from dataclasses import fields, is_dataclass
from gettext import gettext as _

import click

from unstructured.ingest.cli.interfaces import (
    CliChunkingConfig,
    CliConfig,
    CliEmbeddingConfig,
    CliPartitionConfig,
    CliPermissionsConfig,
    CliProcessorConfig,
    CliReadConfig,
    CliRetryStrategyConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import logger


def conform_click_options(options: dict):
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)


def extract_config(flat_data: dict, config: t.Type[BaseConfig]) -> BaseConfig:
    """
    To be able to extract a nested dataclass from a flat dictionary (as in one coming
    from a click-based options input), the config class is dynamically looked through for
    nested dataclass fields and new nested dictionaries are created to conform to the
    shape the overall class expects whn parsing from a dict. During the process, this will create
    copies of the original dictionary to avoid pruning fields but this isn't a
    problem since the `from_dict()` method ignores unneeded values.

    Not handling more complex edge cases for now such as nested types i.e Union[List[List[...]]]
    """

    def conform_dict(inner_d: dict, inner_config: t.Type[BaseConfig]):
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
            # Handle the case where the type of a value if a Union (possibly optional)
            if t.get_origin(f_type) is t.Union:
                union_values = t.get_args(f_type)
                # handle List types
                union_values = [
                    t.get_args(u)[0] if t.get_origin(u) is list else u for u in union_values
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
            origin = t.get_origin(f_type)
            if origin:
                f_type = origin
            if is_subclass(f_type, BaseConfig):
                dd[field.name] = conform_dict(inner_d=dd, inner_config=f_type)
        return dd

    adjusted_dict = conform_dict(inner_d=flat_data, inner_config=config)
    return config.from_dict(adjusted_dict, apply_name_overload=False)


def extract_configs(
    data: dict,
    extras: t.Optional[t.Dict[str, t.Type[BaseConfig]]] = None,
    validate: t.Optional[t.List[t.Type[BaseConfig]]] = None,
    add_defaults: bool = True,
) -> t.Dict[str, BaseConfig]:
    """
    Extract all common configs used across CLI command and validate that any
    command-specific configs have all their needed information from the Click
    options that are passed in during invocation.
    """
    validate = validate if validate else []
    res = (
        {
            "read_config": extract_config(flat_data=data, config=CliReadConfig),
            "partition_config": extract_config(flat_data=data, config=CliPartitionConfig),
            "embedding_config": extract_config(flat_data=data, config=CliEmbeddingConfig),
            "chunking_config": extract_config(flat_data=data, config=CliChunkingConfig),
            "processor_config": extract_config(flat_data=data, config=CliProcessorConfig),
            "permissions_config": extract_config(flat_data=data, config=CliPermissionsConfig),
            "retry_strategy_config": extract_config(flat_data=data, config=CliRetryStrategyConfig),
        }
        if add_defaults
        else {}
    )
    if extras:
        for k, conf in extras.items():
            try:
                res[k] = extract_config(flat_data=data, config=conf)
            except Exception as e:
                logger.error(f"failed to extract config from {conf.__name__}")
                raise e
    for v in validate:
        try:
            extract_config(flat_data=data, config=v)
        except Exception as e:
            raise Exception(f"failed to validate config {v.__name__}") from e

    return res


def add_options(
    cmd: click.Command, extras: t.List[t.Type[CliConfig]], is_src: bool = True
) -> click.Command:
    configs: t.List[t.Type[CliConfig]] = (
        [
            CliPartitionConfig,
            CliReadConfig,
            CliEmbeddingConfig,
            CliChunkingConfig,
            CliProcessorConfig,
            CliPermissionsConfig,
            CliRetryStrategyConfig,
        ]
        if is_src
        else []
    )
    # make sure what's unique to this cmd appears first
    extras.extend(configs)
    for config in extras:
        try:
            config.add_cli_options(cmd=cmd)
        except ValueError as e:
            raise ValueError(f"failed to set configs from {config.__name__}: {e}")
    return cmd


class Group(click.Group):
    def parse_args(self, ctx, args):
        """
        This allows for subcommands to be called with the --help flag without breaking
        if parent command is missing any of its required parameters
        """

        try:
            return super().parse_args(ctx, args)
        except click.MissingParameter:
            if "--help" not in args:
                raise

            # remove the required params so that help can display
            for param in self.params:
                param.required = False
            return super().parse_args(ctx, args)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Copy of the original click.Group format_commands() method but replacing
        'Commands' -> 'Destinations'
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            if formatter.width:
                limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)
            else:
                limit = -6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                with formatter.section(_("Destinations")):
                    formatter.write_dl(rows)
