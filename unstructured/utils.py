from typing import List, Dict

import json


def save_as_jsonl(data: List[Dict], filename: str) -> None:
    with open(filename, "w+") as output_file:
        output_file.writelines((json.dumps(datum) + "\n" for datum in data))


def read_from_jsonl(filename: str) -> List[Dict]:
    with open(filename, "r") as input_file:
        return [json.loads(line) for line in input_file]
