from gettext import gettext as _

import click


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
