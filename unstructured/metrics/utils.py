import logging
import os
import re
import statistics
from typing import List, Optional, Union

import click
import pandas as pd

from unstructured.staging.base import elements_from_json, elements_to_text

logger = logging.getLogger("unstructured.eval")


def _prepare_output_cct(docpath: str, output_type: str):
    try:
        if output_type == "json":
            output_cct = elements_to_text(elements_from_json(docpath))
        elif output_type == "txt":
            output_cct = _read_text_file(docpath)
        else:
            raise ValueError(
                f"File type not supported. Expects one of `json` or `txt`, \
                    but received {output_type} instead."
            )
    except ValueError as e:
        logger.error(f"Could not read the file {docpath}")
        raise e
    return output_cct


def _listdir_recursive(dir: str):
    listdir = []
    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            # Remove the starting directory from the path to show the relative path
            relative_path = os.path.relpath(dirpath, dir)
            if relative_path == ".":
                listdir.append(filename)
            else:
                listdir.append(f"{relative_path}/{filename}")
    return listdir


def _format_grouping_output(*df):
    return pd.concat(df, axis=1).reset_index()


def _display(df):
    if len(df) == 0:
        return
    headers = df.columns.tolist()
    col_widths = [
        max(len(header), max(len(str(item)) for item in df[header])) for header in headers
    ]
    click.echo(" ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers)))
    click.echo("-" * sum(col_widths) + "-" * (len(headers) - 1))
    for _, row in df.iterrows():
        formatted_row = []
        for item in row:
            if isinstance(item, float):
                formatted_row.append(f"{item:.3f}")
            else:
                formatted_row.append(str(item))
        click.echo(
            " ".join(formatted_row[i].ljust(col_widths[i]) for i in range(len(formatted_row))),
        )


def _write_to_file(
    dir: str, filename: str, df: pd.DataFrame, mode: str = "w", overwrite: bool = True
):
    if mode not in ["w", "a"]:
        raise ValueError("Mode not supported. Mode must be one of [w, a].")
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    if "count" in df.columns:
        df["count"] = df["count"].astype(int)
    if "filename" in df.columns and "connector" in df.columns:
        df.sort_values(by=["connector", "filename"], inplace=True)
    if not overwrite:
        filename = _get_non_duplicated_filename(dir, filename)
    df.to_csv(os.path.join(dir, filename), sep="\t", mode=mode, index=False, header=(mode == "w"))


def _sorting_key(filename):
    # Regular expression to find the number in the filename
    numbers = re.findall(r"(\d+)", filename)
    if numbers:
        # If there's a number, return it as an integer for sorting
        return int(numbers[-1])
    else:
        # If no number, return 0 so these files come first
        return 0


def _uniquity_file(file_list, target_filename):
    original_filename, extension = target_filename.rsplit(".", 1)
    pattern = rf"^{re.escape(original_filename)}(?: \((\d+)\))?\.{re.escape(extension)}$"
    duplicated_files = sorted([f for f in file_list if re.match(pattern, f)], key=_sorting_key)

    numbers = []
    for file in duplicated_files:
        match = re.search(r"\((\d+)\)", file)
        if match:
            numbers.append(int(match.group(1)))

    numbers.sort()

    counter = 1
    for number in numbers:
        if number == counter:
            counter += 1
        else:
            break

    return original_filename + " (" + str(counter) + ")." + extension


def _get_non_duplicated_filename(dir, filename):
    filename = _uniquity_file(os.listdir(dir), filename)
    return filename


def _mean(scores: Union[pd.Series, List[float]], rounding: Optional[int] = 3):
    if len(scores) == 0:
        return None
    mean = statistics.mean(scores)
    if not rounding:
        return mean
    return round(mean, rounding)


def _stdev(scores: List[Optional[float]], rounding: Optional[int] = 3):
    # Filter out None values
    scores = [score for score in scores if score is not None]
    # Proceed only if there are more than one value
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.stdev(scores)
    return round(statistics.stdev(scores), rounding)


def _pstdev(scores: List[Optional[float]], rounding: Optional[int] = 3):
    scores = [score for score in scores if score is not None]
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.pstdev(scores)
    return round(statistics.pstdev(scores), rounding)


def _read_text_file(path):
    # Check if the file exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file at {path} does not exist.")

    try:
        with open(path, errors="ignore") as f:
            text = f.read()
        return text
    except OSError as e:
        # Handle other I/O related errors
        raise IOError(f"An error occurred when reading the file at {path}: {e}")
