#! /usr/bin/env python3

from typing import List, Optional, Tuple

import click

from unstructured.metrics.evaluate import (
    get_mean_grouping,
    measure_element_type_accuracy,
    measure_table_structure_accuracy,
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
@click.option(
    "--output_type",
    type=str,
    default="json",
    show_default=True,
    help="Takes in either `txt` or `json` as output_type.",
)
def measure_text_extraction_accuracy_command(
    output_dir: str,
    source_dir: str,
    export_dir: str,
    weights: Tuple[int, int, int],
    visualize: bool,
    output_type: str,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    grouping: Optional[str] = None,
):
    return measure_text_extraction_accuracy(
        output_dir,
        source_dir,
        output_list,
        source_list,
        export_dir,
        grouping,
        weights,
        visualize,
        output_type,
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
    export_dir: str,
    visualize: bool,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
):
    return measure_element_type_accuracy(
        output_dir, source_dir, output_list, source_list, export_dir, visualize
    )


@main.command()
@click.option(
    "--grouping",
    type=str,
    required=True,
    help="The category to group by; valid values are 'doctype' and 'connector'.",
)
@click.option(
    "--data_input",
    type=str,
    required=True,
    help="A datafram or path to the CSV/TSV file containing the data",
)
@click.option(
    "--export_dir",
    type=str,
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        your/working/dir/metrics/",
)
@click.option(
    "--eval_name",
    type=str,
    help="Evaluated metric. Expecting one of 'text_extraction' or 'element_type'",
)
def get_mean_grouping_command(grouping: str, data_input: str, export_dir: str, eval_name: str):
    return get_mean_grouping(grouping, data_input, export_dir, eval_name)


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
@click.option(
    "--cutoff",
    type=float,
    show_default=True,
    default=0.8,
    help="The cutoff value for the element level alignment. \
        If not set, a default value is used",
)
def measure_table_structure_accuracy_command(
    output_dir: str,
    source_dir: str,
    export_dir: str,
    visualize: bool,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    cutoff: Optional[float] = None,
):
    return measure_table_structure_accuracy(
        output_dir, source_dir, output_list, source_list, export_dir, visualize, cutoff
    )


if __name__ == "__main__":
    main()
