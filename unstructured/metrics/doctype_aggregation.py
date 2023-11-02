import os
from typing import List, Optional, Tuple

import click
import numpy as np
import pandas as pd

from unstructured.ingest.evaluate import measure_text_edit_distance
from unstructured.ingest.evaluate import _write_to_file

@click.group()
def main():
    pass

def aggregate_cct_data_by_doctype(results_dir: str):
    # load tsv into dataframe
    df = pd.read_csv(os.path.join(results_dir, "all-docs-cct.tsv"), sep='\t', header=0)

    # group by doctype
    # df.groupby(by="doctype").mean()
    # df.groupby(by="doctype").std()
    # df.groupby(by="doctype").agg(np.std, ddof=0)
    agg_df = df.groupby(by="doctype").agg(['mean', 'std'])

    # calculate stats (using eval functions or pandas)

    # write results to same export results folder
    _write_to_file(results_dir, "all-docs-cct.tsv", agg_df, ["mean", "sample_sd"])



@main.command()
@click.option("--output_dir", type=str, help="Directory to structured output.")
@click.option(
    "--output_list",
    type=str,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be use.",
)
@click.option("--source_dir", type=str, help="Directory to source.")
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
def holistic_script_cct_entry_point(
    output_dir: str,
    output_list: Optional[List[str]],
    source_dir: str,
    source_list: Optional[List[str]],
    export_dir: str,
    weights: Tuple[int, int, int],
) -> None:
    export_dir = "result_doctype_aggregate"
    measure_text_edit_distance(output_dir, output_list, source_dir, source_list, export_dir, weights)
    aggregate_cct_data_by_doctype(export_dir)


if __name__ == "__main__":
    main()