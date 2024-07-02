from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString, Dict


@dataclass
class PartitionerCliConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--strategy"],
                default="auto",
                help="The method that will be used to process the documents. "
                "Default: auto. Other strategies include `fast` and `hi_res`.",
            ),
            click.Option(
                ["--ocr-languages"],
                default=None,
                type=DelimitedString(delimiter="+"),
                help="A list of language packs to specify which languages to use for OCR, "
                "separated by '+' e.g. 'eng+deu' to use the English and German language packs. "
                "The appropriate Tesseract "
                "language pack needs to be installed.",
            ),
            click.Option(
                ["--encoding"],
                default=None,
                help="Text encoding to use when reading documents. By default the encoding is "
                "detected automatically.",
            ),
            click.Option(
                ["--skip-infer-table-types"],
                type=DelimitedString(),
                default=None,
                help="Optional list of document types to skip table extraction on",
            ),
            click.Option(
                ["--additional-partition-args"],
                type=Dict(),
                help="A json string representation of values to pass through to partition()",
            ),
            click.Option(
                ["--fields-include"],
                type=DelimitedString(),
                default=["element_id", "text", "type", "metadata", "embeddings"],
                help="Comma-delimited list. If set, include the specified top-level "
                "fields in an element.",
            ),
            click.Option(
                ["--flatten-metadata"],
                is_flag=True,
                default=False,
                help="Results in flattened json elements. "
                "Specifically, the metadata key values are brought to "
                "the top-level of the element, and the `metadata` key itself is removed.",
            ),
            click.Option(
                ["--metadata-include"],
                default=[],
                type=DelimitedString(),
                help="Comma-delimited list. If set, include the specified metadata "
                "fields if they exist and drop all other fields. ",
            ),
            click.Option(
                ["--metadata-exclude"],
                default=[],
                type=DelimitedString(),
                help="Comma-delimited list. If set, drop the specified metadata "
                "fields if they exist.",
            ),
            click.Option(
                ["--partition-by-api"],
                is_flag=True,
                default=False,
                help="Use a remote API to partition the files."
                " Otherwise, use the function from partition.auto",
            ),
            click.Option(
                ["--partition-endpoint"],
                default="https://api.unstructured.io/general/v0/general",
                help="If partitioning via api, use the following host. "
                "Default: https://api.unstructured.io/general/v0/general",
            ),
            click.Option(
                ["--api-key"],
                default=None,
                help="API Key for partition endpoint.",
            ),
            click.Option(
                ["--hi-res-model-name"],
                default=None,
                help="Model name for hi-res strategy.",
            ),
        ]
        return options
