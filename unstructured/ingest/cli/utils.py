import typing as t
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


def conform_click_options(options: dict):
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)


def extract_configs(
    data: dict,
    extras: t.Optional[t.Dict[str, t.Type[BaseConfig]]] = None,
    validate: t.Optional[t.List[t.Type[BaseConfig]]] = None,
) -> t.Dict[str, BaseConfig]:
    """
    Extract all common configs used across CLI command and validate that any
    command-specific configs have all their needed information from the Click
    options that are passed in during invocation.
    """
    validate = validate if validate else []
    res = {
        "read_config": CliReadConfig.from_dict(data),
        "partition_config": CliPartitionConfig.from_dict(data),
        "embedding_config": CliEmbeddingConfig.from_dict(data),
        "chunking_config": CliChunkingConfig.from_dict(data),
        "processor_config": CliProcessorConfig.from_dict(data),
        "permissions_config": CliPermissionsConfig.from_dict(data),
        "retry_strategy_config": CliRetryStrategyConfig.from_dict(data),
    }
    if extras:
        for k, conf in extras.items():
            res[k] = conf.from_dict(data)
    for v in validate:
        v.from_dict(data)
    return res


def add_options(cmd: click.Command, extras=t.List[t.Type[CliConfig]], is_src=True) -> click.Command:
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
    configs.extend(extras)
    for config in configs:
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
