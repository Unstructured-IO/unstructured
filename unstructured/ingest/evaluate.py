#! /usr/bin/env python3

from typing import List, Optional, Tuple

import click

from unstructured.metrics.evaluate import measure_element_type_accuracy, measure_text_edit_distance


@click.group()
def main():
    pass


@main.command()
@click.option("--output_dir", type=str, help="Directory to structured output.")
@click.option("--source_dir", type=str, help="Directory to source.")
@click.option(
    "--output_list",
    type=str,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be use.",
)
@click.option(
    "--source_list",
    type=str,
    multiple=True,
    help="Optional: list of selected source file names under the directory \
        to be evaluate. If none, all files under directory will be use.",
)
@click.option(
    "--export_dir",
    type=str,
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        your/working/dir/metrics/",
)
@click.option(
    "--weights",
    type=(int, int, int),
    default=(2, 1, 1),
    show_default=True,
    help="A tuple of weights to the Levenshtein distance calculation. \
        See text_extraction.py/calculate_edit_distance for more details.",
)
def measure_text_edit_distance_command(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]],
    source_list: Optional[List[str]],
    export_dir: str,
    weights: Tuple[int, int, int],
):
    return measure_text_edit_distance(
        output_dir, source_dir, output_list, source_list, export_dir, weights
    )


@main.command()
@click.option("--output_dir", type=str, help="Directory to structured output.")
@click.option("--source_dir", type=str, help="Directory to structured source.")
@click.option(
    "--output_list",
    type=str,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be used.",
)
@click.option(
    "--source_list",
    type=str,
    multiple=True,
    help="Optional: list of selected source file names under the directory \
        to be evaluate. If none, all files under directory will be used.",
)
@click.option(
    "--export_dir",
    type=str,
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        your/working/dir/metrics/",
)
def measure_element_type_accuracy_command(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]],
    source_list: Optional[List[str]],
    export_dir: str,
):
    return measure_element_type_accuracy(
        output_dir, source_dir, output_list, source_list, export_dir
    )


if __name__ == "__main__":
    main()
