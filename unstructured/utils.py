import importlib
import json
from typing import Dict, List, Optional, Union


def save_as_jsonl(data: List[Dict], filename: str) -> None:
    with open(filename, "w+") as output_file:
        output_file.writelines(json.dumps(datum) + "\n" for datum in data)


def read_from_jsonl(filename: str) -> List[Dict]:
    with open(filename) as input_file:
        return [json.loads(line) for line in input_file]


def requires_dependencies(deps: Union[str, List[str]], extras: Optional[str] = None):
    def decorator(cls):
        if isinstance(deps, str):
            deps = [deps]
        missing_deps = []
        for dep in deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing_deps.append(dep)
        if len(missing_deps) > 0:
            raise ImportError(
                f"Following dependencies are missing: {', '.join(missing_deps)}."
                + f"Please install them using `pip install unstructured[{extras}]`."
                if extras
                else f"Please install them using `pip install {' '.join(missing_deps)}`.",
            )
        return cls

    return decorator
