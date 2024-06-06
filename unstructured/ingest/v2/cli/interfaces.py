from abc import ABC, abstractmethod

import click


class CliConfig(ABC):
    @staticmethod
    @abstractmethod
    def get_cli_options() -> list[click.Option]:
        pass

    @classmethod
    def add_cli_options(cls, cmd: click.Command) -> None:
        options_to_add = cls.get_cli_options()
        CliConfig.add_params(cmd, params=options_to_add)

    @staticmethod
    def add_params(cmd: click.Command, params: list[click.Parameter]):
        existing_opts = []
        for param in cmd.params:
            existing_opts.extend(param.opts)
        for param in params:
            for opt in param.opts:
                if opt in existing_opts:
                    raise ValueError(f"{opt} is already defined on the command {cmd.name}")
                existing_opts.append(opt)
                cmd.params.append(param)
