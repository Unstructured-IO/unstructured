#! /usr/bin/env python3

import click
import os
import json
import csv
import statistics

from typing import List, Optional, Tuple

from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.staging.base import elements_to_text, elements_from_json


@click.command()
@click.option("--output_dir", type=click.STRING, help="Directory to a structured output.")
@click.option("--output_list", type=click.STRING, multiple=True, help="Optional: list of selected structured output file names under the directory to be evaluate. If none, all files under directory will be use.")
@click.option("--source_dir", type=click.STRING, help="Directory to a cct source.")
@click.option("--source_list", type=click.STRING, multiple=True, help="Optional: list of selected cct source file names under the directory to be evaluate. If none, all files under directory will be use.")
@click.option("--export_dir", type=click.STRING, default="evaluation_metrics", help="Directory to save the output evaluation metrics to. Default to [your_working_dir]/evaluation_metrics/")
@click.option("--weights", type=(click.INT, click.INT, click.INT), default=(2, 1, 1), show_default=True, help="A tuple of weights to the Levenshtein distance calculation. See text_extraction/calculate_edit_distance for more details.")
def measure_edit_distance(
    output_dir: str,
    output_list: Optional[Tuple[str, ...]],
    source_dir: str,
    source_list: Optional[Tuple[str, ...]],
    export_dir: str = "evaluation_metrics",
    weights: Tuple[int, int, int] = (2, 1, 1),
) -> float:
    
    if not output_list:
        output_list = os.listdir(f"{output_dir}")
    if not source_list:
        source_list = os.listdir(f"{source_dir}")

    accuracy_scores = []
    percent_missing_scores = []

    for doc in output_list:
        fn = (doc.split("/")[-1]).split(".json")[0]
        connector = doc.split("/")[0]
        if fn + ".txt" in source_list:
            click.echo(doc)
            click.echo(output_dir)
            click.echo(os.path.join(output_dir, doc))
            output_cct = elements_to_text(elements_from_json(json.loads(os.path.join(output_dir, doc))))
            with open(f"{os.path.join(source_dir, fn)}") as f:
                source_cct = f.read() 
            accuracy = calculate_accuracy(output_cct, source_cct, weights)
            percent_missing = calculate_percent_missing_text(output_cct, source_cct)

            headers = ["filename", "connector", "cct-accuracy", "cct-%missing"]
            row = [fn, connector, accuracy, percent_missing]
            _write_to_file(export_dir, "all-docs-cct.tsv", row, headers)

            accuracy_scores.append(accuracy)
            percent_missing_scores.append(percent_missing)
            print(accuracy)
            print(percent_missing)
    
    headers = ["strategy", "average", "sample_sd", "population_sd"]
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", ["cct-accuracy", statistics.mean(accuracy_scores), statistics.stdev(accuracy_scores), statistics.pstdev(accuracy_scores)], headers)
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", ["cct-%missing", statistics.mean(percent_missing_scores), statistics.stdev(percent_missing_scores), statistics.pstdev(percent_missing_scores)], headers)
    
def _write_to_file(dir, filename, row, headers):
    file_existed = os.path.isfile(os.path.join(dir, filename))
    with open(filename, "a") as tsv:
        
        writer = csv.writer(tsv, delimiter="\t", fieldnames=headers)

        if not file_existed:
            writer.writeheader()
        
        writer.writerow(row)

if __name__ == "__main__":
    measure_edit_distance()