from typing import Dict, List

from unstructured.file_utils.filetype import FileType

VALID_STRATEGIES: Dict[str, List[FileType]] = {
    "hi_res": [
        FileType.PDF,
        FileType.JPG,
        FileType.PNG,
    ],
    "ocr_only": [
        FileType.PDF,
        FileType.JPG,
        FileType.PNG,
    ],
    "fast": [
        FileType.PDF,
    ],
}


def validate_strategy(strategy: str, filetype: FileType):
    """Determines if the strategy is valid for the specified filetype."""
    valid_filetypes = VALID_STRATEGIES.get(strategy, None)
    if valid_filetypes is None:
        raise ValueError(f"{strategy} is not a valid strategy.")
    if filetype not in valid_filetypes:
        raise ValueError(f"{strategy} is not a valid strategy for filetype {filetype}.")
