#! /usr/bin/env python3

from typing import List, Optional, Tuple

import click

from unstructured.metrics.evaluate import (
    measure_element_type_accuracy,
    measure_text_extraction_accuracy,
)


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
@click.option("--grouping", type=str, help="Input field for aggregration, or leave blank if none.")
@click.option(
    "--weights",
    type=(int, int, int),
    default=(2, 1, 1),
    show_default=True,
    help="A list of weights to the Levenshtein distance calculation. Takes input as --weights 2 2 2\
        See text_extraction.py/calculate_edit_distance for more details.",
)
@click.option(
    "--visualize",
    is_flag=True,
    show_default=True,
    default=False,
    help="Add the flag to show progress bar.",
)
def measure_text_extraction_accuracy_command(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]],
    source_list: Optional[List[str]],
    export_dir: str,
    grouping: Optional[str],
    weights: Tuple[int, int, int],
    visualize: bool,
):
    return measure_text_extraction_accuracy(
        output_dir, source_dir, output_list, source_list, export_dir, grouping, weights, visualize
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
@click.option(
    "--visualize",
    is_flag=True,
    show_default=True,
    default=False,
    help="Add the flag to show progress bar.",
)
def measure_element_type_accuracy_command(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]],
    source_list: Optional[List[str]],
    export_dir: str,
    visualize: bool,
):
    return measure_element_type_accuracy(
        output_dir, source_dir, output_list, source_list, export_dir, visualize
    )


if __name__ == "__main__":
    main()
