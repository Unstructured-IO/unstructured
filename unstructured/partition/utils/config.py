"""
This module contains variables that can permitted to be tweaked by the system environment. For
example, model parameters that changes the output of an inference call. Constants do NOT belong in
this module. Constants are values that are usually names for common options (e.g., color names) or
settings that should not be altered without making a code change (e.g., definition of 1Gb of memory
in bytes). Constants should go into `./constants.py`
"""

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from unstructured.partition.utils.constants import OCR_AGENT_TESSERACT


@lru_cache(maxsize=1)
def get_tempdir(dir: str) -> str:
    tempdir = Path(dir) / f"tmp/{os.getpgid(0)}"
    return str(tempdir)


@dataclass
class ENVConfig:
    """class for configuring enviorment parameters"""

    def __post_init__(self):
        if self.GLOBAL_WORKING_DIR_ENABLED:
            self._setup_tmpdir(self.GLOBAL_WORKING_PROCESS_DIR)

    def _get_string(self, var: str, default_value: str = "") -> str:
        """attempt to get the value of var from the os environment; if not present return the
        default_value"""
        return os.environ.get(var, default_value)

    def _get_int(self, var: str, default_value: int) -> int:
        if value := self._get_string(var):
            return int(value)
        return default_value

    def _get_float(self, var: str, default_value: float) -> float:
        if value := self._get_string(var):
            return float(value)
        return default_value

    def _get_bool(self, var: str, default_value: bool) -> bool:
        if value := self._get_string(var):
            return value.lower() in ("true", "1", "t")
        return default_value

    def _setup_tmpdir(self, tmpdir: str) -> None:
        Path(tmpdir).mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = tmpdir

    @property
    def IMAGE_CROP_PAD(self) -> int:
        """extra image content to add around an identified element region; measured in pixels"""
        return self._get_int("IMAGE_CROP_PAD", 0)

    @property
    def TABLE_IMAGE_CROP_PAD(self) -> int:
        """extra image content to add around an identified table region; measured in pixels

        The padding adds image data around an identified table bounding box for downstream table
        structure detection model use as input
        """
        return self._get_int("TABLE_IMAGE_CROP_PAD", 0)

    @property
    def TESSERACT_TEXT_HEIGHT_QUANTILE(self) -> float:
        """the quantile to check for text height"""
        return self._get_float("TESSERACT_TEXT_HEIGHT_QUANTILE", 0.5)

    @property
    def TESSERACT_MIN_TEXT_HEIGHT(self) -> int:
        """minimum text height acceptable from tesseract OCR results

        if estimated text height from tesseract OCR results is lower than this value the image is
        scaled up to be processed again
        """
        return self._get_int("TESSERACT_MIN_TEXT_HEIGHT", 12)

    @property
    def TESSERACT_MAX_TEXT_HEIGHT(self) -> int:
        """maximum text height acceptable from tesseract OCR results

        if estimated text height from tesseract OCR results is higher than this value the image is
        scaled down to be processed again
        """
        return self._get_int("TESSERACT_MAX_TEXT_HEIGHT", 100)

    @property
    def TESSERACT_OPTIMUM_TEXT_HEIGHT(self) -> int:
        """optimum text height for tesseract OCR"""
        return self._get_int("TESSERACT_OPTIMUM_TEXT_HEIGHT", 20)

    @property
    def GOOGLEVISION_API_ENDPOINT(self) -> str:
        """API endpoint to use for Google Vision"""
        return self._get_string("GOOGLEVISION_API_ENDPOINT", "")

    @property
    def OCR_AGENT(self) -> str:
        """OCR Agent to use"""
        return self._get_string("OCR_AGENT", OCR_AGENT_TESSERACT)

    @property
    def EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD(self) -> int:
        """extra image block content to add around an identified element(`Image`, `Table`) region
        horizontally; measured in pixels
        """
        return self._get_int("EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD", 0)

    @property
    def EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD(self) -> int:
        """extra image block content to add around an identified element(`Image`, `Table`) region
        vertically; measured in pixels
        """
        return self._get_int("EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD", 0)

    @property
    def EXTRACT_TABLE_AS_CELLS(self) -> bool:
        """adds `table_as_cells` to a Table element's metadata when it is True"""
        return self._get_bool("EXTRACT_TABLE_AS_CELLS", False)

    @property
    def OCR_LAYOUT_SUBREGION_THRESHOLD(self) -> float:
        """threshold to determine if an OCR region is a sub-region of a given block
        when aggregating the text from OCR'd elements that lie within the given block

        When the intersection region area divided by self area is larger than this threshold self is
        considered a subregion of the other
        """
        return self._get_float("OCR_LAYOUT_SUBREGION_THRESHOLD", 0.5)

    @property
    def EMBEDDED_IMAGE_SAME_REGION_THRESHOLD(self) -> float:
        """threshold to consider the bounding boxes of two embedded images as the same region"""
        return self._get_float("EMBEDDED_IMAGE_SAME_REGION_THRESHOLD", 0.6)

    @property
    def EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD(self) -> float:
        """threshold to determine if an embedded region is a sub-region of a given block
        when aggregating the text from embedded elements that lie within the given block

        When the intersection region area divided by self area is larger than this threshold self is
        considered a subregion of the other
        """
        return self._get_float("EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD", 0.99)

    @property
    def PDF_ANNOTATION_THRESHOLD(self) -> float:
        """The threshold value (between 0.0 and 1.0) that determines the minimum overlap required
        for an annotation to be considered within the element.
        """

        return self._get_float("PDF_ANNOTATION_THRESHOLD", 0.9)

    @property
    def GLOBAL_WORKING_DIR_ENABLED(self) -> bool:
        """Enable usage of GLOBAL_WORKING_DIR and GLOBAL_WORKING_PROCESS_DIR."""
        return self._get_bool("GLOBAL_WORKING_DIR_ENABLED", False)

    @property
    def GLOBAL_WORKING_DIR(self) -> str:
        """Path to Unstructured cache directory."""
        return self._get_string("GLOBAL_WORKING_DIR", str(Path.home() / ".cache/unstructured"))

    @property
    def GLOBAL_WORKING_PROCESS_DIR(self) -> str:
        """Path to Unstructured cache tempdir. Overrides TMPDIR, TEMP and TMP.
        Defaults to '{GLOBAL_WORKING_DIR}/tmp/{os.getpgid(0)}'.
        """
        default_tmpdir = get_tempdir(dir=self.GLOBAL_WORKING_DIR)
        tmpdir = self._get_string("GLOBAL_WORKING_PROCESS_DIR", default_tmpdir)
        if tmpdir == "":
            tmpdir = default_tmpdir
        if self.GLOBAL_WORKING_DIR_ENABLED:
            self._setup_tmpdir(tmpdir)
        return tmpdir


env_config = ENVConfig()
