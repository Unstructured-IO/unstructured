import typing as t
from gettext import gettext as _
from gettext import ngettext

import click


def conform_click_options(options: dict):
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)


class DelimitedString(click.ParamType):
    name = "delimited-string"

    def __init__(self, delimiter: str = ",", choices: t.Optional[t.List[str]] = None):
        self.choices = choices if choices else []
        self.delimiter = delimiter

    def convert(
        self,
        value: t.Any,
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> t.Any:
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
