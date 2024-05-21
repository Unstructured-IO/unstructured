from dataclasses import dataclass

import click

from unstructured.chunking import CHUNK_MAX_CHARS_DEFAULT, CHUNK_MULTI_PAGE_DEFAULT
from unstructured.ingest.v2.cli.interfaces import CliConfig


@dataclass
class ChunkerCliConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--chunking-strategy"],
                type=str,
                default=None,
                help="The rule-set to use to form chunks. Omit to disable chunking.",
            ),
            click.Option(
                ["--chunk-combine-text-under-n-chars"],
                type=int,
                help=(
                    "Combine consecutive chunks when the first does not exceed this length and"
                    " the second will fit without exceeding the hard-maximum length. Only"
                    " operative for 'by_title' chunking-strategy."
                ),
            ),
            click.Option(
                ["--chunk-include-orig-elements/--chunk-no-include-orig-elements"],
                is_flag=True,
                default=True,
                help=(
                    "When chunking, add the original elements consolidated to form each chunk to"
                    " `.metadata.orig_elements` on that chunk."
                ),
            ),
            click.Option(
                ["--chunk-max-characters"],
                type=int,
                default=CHUNK_MAX_CHARS_DEFAULT,
                show_default=True,
                help=(
                    "Hard maximum chunk length. No chunk will exceed this length. An oversized"
                    " element will be divided by text-splitting to fit this window."
                ),
            ),
            click.Option(
                ["--chunk-multipage-sections/--chunk-no-multipage-sections"],
                is_flag=True,
                default=CHUNK_MULTI_PAGE_DEFAULT,
                help=(
                    "Ignore page boundaries when chunking such that elements from two different"
                    " pages can appear in the same chunk. Only operative for 'by_title'"
                    " chunking-strategy."
                ),
            ),
            click.Option(
                ["--chunk-new-after-n-chars"],
                type=int,
                help=(
                    "Soft-maximum chunk length. Another element will not be added to a chunk of"
                    " this length even when it would fit without exceeding the hard-maximum"
                    " length."
                ),
            ),
            click.Option(
                ["--chunk-overlap"],
                type=int,
                default=0,
                show_default=True,
                help=(
                    "Prefix chunk text with last overlap=N characters of prior chunk. Only"
                    " applies to oversized chunks divided by text-splitting. To apply overlap to"
                    " non-oversized chunks use the --overlap-all option."
                ),
            ),
            click.Option(
                ["--chunk-overlap-all"],
                is_flag=True,
                default=False,
                help=(
                    "Apply overlap to chunks formed from whole elements as well as those formed"
                    " by text-splitting oversized elements. Overlap length is take from --overlap"
                    " option value."
                ),
            ),
        ]
        return options
