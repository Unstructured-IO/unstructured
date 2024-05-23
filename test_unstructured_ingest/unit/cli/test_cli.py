import click
import pytest

from unstructured.ingest.cli.interfaces import CliMixin


def test_add_params():
    @click.command()
    def sample_cmd():
        pass

    options = [
        click.Option(["--opt1"]),
        click.Option(["--opt1"]),
    ]
    cmd = sample_cmd
    with pytest.raises(ValueError):
        CliMixin.add_params(cmd=cmd, params=options)
