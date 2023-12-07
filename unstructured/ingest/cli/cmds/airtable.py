import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.airtable import SimpleAirtableConfig


@dataclass
class AirtableCliConfig(SimpleAirtableConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--personal-access-token"],
                default=None,
                help="Personal access token to authenticate into Airtable. Check: "
                "https://support.airtable.com/docs/creating-and-using-api-keys-and-access-tokens "
                "for more info",
            ),
            click.Option(
                ["--list-of-paths"],
                default=None,
                help="""
        A list of paths that specify the locations to ingest data from within Airtable.

        If this argument is not set, the connector ingests all tables within each and every base.
        --list-of-paths: path1 path2 path3 ….
        path: base_id/table_id(optional)/view_id(optional)/

        To obtain (base, table, view) ids in bulk, check:
        https://airtable.com/developers/web/api/list-bases (base ids)
        https://airtable.com/developers/web/api/get-base-schema (table and view ids)
        https://pyairtable.readthedocs.io/en/latest/metadata.html (base, table and view ids)

        To obtain specific ids from Airtable UI, go to your workspace, and copy any
        relevant id from the URL structure:
        https://airtable.com/appAbcDeF1ghijKlm/tblABcdEfG1HIJkLm/viwABCDEfg6hijKLM
        appAbcDeF1ghijKlm -> base_id
        tblABcdEfG1HIJkLm -> table_id
        viwABCDEfg6hijKLM -> view_id

        You can also check: https://support.airtable.com/docs/finding-airtable-ids

        Here is an example for one --list-of-paths:
            base1/		→ gets the entirety of all tables inside base1
            base1/table1		→ gets all rows and columns within table1 in base1
            base1/table1/view1	→ gets the rows and columns that are
                                  visible in view1 for the table1 in base1

        Examples to invalid airtable_paths:
            table1          → has to mention base to be valid
            base1/view1     → has to mention table to be valid
                """,
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="airtable",
        cli_config=AirtableCliConfig,
    )
    return cmd_cls
