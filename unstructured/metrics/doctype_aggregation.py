import os
from typing import List, Optional, Tuple

import click
import pandas as pd

from unstructured.metrics.evaluate import measure_text_edit_distance


@click.group()
def main():
    pass


def aggregate_cct_data_by_doctype(results_dir: str):
    # load tsv into dataframe
    df = pd.read_csv(os.path.join(results_dir, "all-docs-cct.tsv"), sep="\t", header=0)

    # group by doctype and calculate stats
    agg_df = df.groupby("doctype").agg(
        {"cct-accuracy": ["mean", "std", "count"], "cct-%missing": ["mean", "std", "count"]}
    )

    # write results to same export results folder
    agg_df.to_csv(os.path.join(results_dir, "all-doctypes-agg-cct.tsv"))


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
    default="metrics_results",
    help="Directory to save the output evaluation metrics to. Default to \
        [your_working_dir]/metrics_results/",
)
@click.option(
    "--weights",
    type=(int, int, int),
    default=(2, 1, 1),
    show_default=True,
    help="A tuple of weights to the Levenshtein distance calculation. \
        See text_extraction.py/calculate_edit_distance for more details.",
)
def measure_holistic_eval_cct(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]],
    source_list: Optional[List[str]],
    export_dir: str,
    weights: Tuple[int, int, int],
) -> None:
    export_dir = "result_doctype_aggregate"
    measure_text_edit_distance(
        output_dir=output_dir,
        source_dir=source_dir,
        output_list=output_list,
        source_list=source_list,
        export_dir=export_dir,
        weights=weights,
    )
    aggregate_cct_data_by_doctype(export_dir)


if __name__ == "__main__":
    main()
