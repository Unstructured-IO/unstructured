"""
This module contains variables that can permitted to be tweaked by the system environment. For
example, model parameters that changes the output of an inference call. Constants do NOT belong in
this module. Constants are values that are usually names for common options (e.g., color names) or
settings that should not be altered without making a code change (e.g., definition of 1Gb of memory
in bytes). Constants should go into `./constants.py`
"""
import os
from dataclasses import dataclass

from unstructured.partition.utils.constants import OCR_AGENT_TESSERACT


@dataclass
class ENVConfig:
    """class for configuring enviorment parameters"""

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
    def OCR_AGENT(self) -> str:
        """error margin when comparing if a ocr region is within the table element when preparing
        table tokens
        """
        return self._get_string("OCR_AGENT", OCR_AGENT_TESSERACT)


env_config = ENVConfig()
