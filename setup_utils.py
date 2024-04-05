from pathlib import Path
from typing import List, Optional, Union


def load_requirements(file_list: Optional[Union[str, List[str]]] = None) -> List[str]:
    if file_list is None:
        file_list = ["requirements/base.in"]
    if isinstance(file_list, str):
        file_list = [file_list]
    requirements: List[str] = []
    for file in file_list:
        path = Path(file)
        file_dir = path.parent.resolve()
        with open(file, encoding="utf-8") as f:
            raw = f.read().splitlines()
            requirements.extend([r for r in raw if not r.startswith("#") and not r.startswith("-")])
            recursive_reqs = [r for r in raw if r.startswith("-r")]
            if recursive_reqs:
                filenames = []
                for recursive_req in recursive_reqs:
                    file_spec = recursive_req.split()[-1]
                    file_path = Path(file_dir) / file_spec
                    filenames.append(str(file_path.resolve()))
                requirements.extend(load_requirements(file_list=filenames))
    return list(set(requirements))
