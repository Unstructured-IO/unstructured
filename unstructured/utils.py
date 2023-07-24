import importlib
import json
from datetime import datetime
from functools import wraps
from typing import Dict, List, Optional, Union

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d+%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


def save_as_jsonl(data: List[Dict], filename: str) -> None:
    with open(filename, "w+") as output_file:
        output_file.writelines(json.dumps(datum) + "\n" for datum in data)


def read_from_jsonl(filename: str) -> List[Dict]:
    with open(filename) as input_file:
        return [json.loads(line) for line in input_file]


def requires_dependencies(
    dependencies: Union[str, List[str]],
    extras: Optional[str] = None,
):
    if isinstance(dependencies, str):
        dependencies = [dependencies]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            missing_deps = []
            for dep in dependencies:
                if not dependency_exists(dep):
                    missing_deps.append(dep)
            if len(missing_deps) > 0:
                raise ImportError(
                    f"Following dependencies are missing: {', '.join(missing_deps)}. "
                    + (
                        f"""Please install them using `pip install "unstructured[{extras}]"`."""
                        if extras
                        else f"Please install them using `pip install {' '.join(missing_deps)}`."
                    ),
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def dependency_exists(dependency):
    try:
        importlib.import_module(dependency)
    except ImportError as e:
        # Check to make sure this isn't some unrelated import error.
        if dependency in repr(e):
            return False
    return True


# Copied from unstructured/ingest/connector/biomed.py
def validate_date_args(date: Optional[str] = None):
    if not date:
        raise ValueError("The argument date is None.")

    for format in DATE_FORMATS:
        try:
            datetime.strptime(date, format)
            return True
        except ValueError:
            pass

    raise ValueError(
        f"The argument {date} does not satisfy the format: "
        "YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
    )
