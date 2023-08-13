import argparse
import json
from io import StringIO

import pandas as pd


def number_of_rows(file_path):
    with open(file_path) as file:
        data = json.load(file)
        df = pd.read_csv(StringIO(data[0]["text"]))
    return len(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read Unstructured Ingest output file and print the number of rows",
    )

    parser.add_argument(
        "--structured-output-file-path",
        help="Path to Unstructured Ingest output file",
    )

    args = parser.parse_args()

    output_path = args.structured_output_file_path
    print(number_of_rows(output_path))
