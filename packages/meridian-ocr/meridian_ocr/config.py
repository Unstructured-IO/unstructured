"""
This module contains variables that can permitted to be tweaked by the system environment. For
example, model parameters that changes the output of an inference call. Constants do NOT belong in
this module. Constants are values that are usually names for common options (e.g., color names) or
settings that should not be altered without making a code change (e.g., definition of 1Gb of memory
in bytes). Constants should go into `./constants.py`
"""

import os
from dataclasses import dataclass


@dataclass
class InferenceConfig:
    """class for configuring inference parameters"""

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
    def TABLE_IMAGE_BACKGROUND_PAD(self) -> int:
        """number of pixels to pad around an table image with a white background color

        The padding adds NO image data around an identified table bounding box; it simply adds white
        background around the image
        """
        return self._get_int("TABLE_IMAGE_BACKGROUND_PAD", 20)

    @property
    def TT_TABLE_CONF(self) -> float:
        """confidence threshold for table identified by table transformer"""
        return self._get_float("TT_TABLE_CONF", 0.5)

    @property
    def TABLE_COLUMN_CONF(self) -> float:
        """confidence threshold for column identified by table transformer"""
        return self._get_float("TABLE_COLUMN_CONF", 0.5)

    @property
    def TABLE_ROW_CONF(self) -> float:
        """confidence threshold for column identified by table transformer"""
        return self._get_float("TABLE_ROW_CONF", 0.5)

    @property
    def TABLE_COLUMN_HEADER_CONF(self) -> float:
        """confidence threshold for column header identified by table transformer"""
        return self._get_float("TABLE_COLUMN_HEADER_CONF", 0.5)

    @property
    def TABLE_PROJECTED_ROW_HEADER_CONF(self) -> float:
        """confidence threshold for projected row header identified by table transformer"""
        return self._get_float("TABLE_PROJECTED_ROW_HEADER_CONF", 0.5)

    @property
    def TABLE_SPANNING_CELL_CONF(self) -> float:
        """confidence threshold for table spanning cells identified by table transformer"""
        return self._get_float("TABLE_SPANNING_CELL_CONF", 0.5)

    @property
    def TABLE_IOB_THRESHOLD(self) -> float:
        """minimum intersection over box area ratio for a box to be considered part of a larger box
        it intersects"""
        return self._get_float("TABLE_IOB_THRESHOLD", 0.5)

    @property
    def LAYOUT_SAME_REGION_THRESHOLD(self) -> float:
        """threshold for two layouts' bounding boxes to be considered as the same region

        When the intersection area over union area of the two is larger than this threshold the two
        boxes are considered the same region
        """
        return self._get_float("LAYOUT_SAME_REGION_THRESHOLD", 0.75)

    @property
    def LAYOUT_SUBREGION_THRESHOLD(self) -> float:
        """threshold for one bounding box to be considered as a sub-region of another bounding box

        When the intersection region area divided by self area is larger than this threshold self is
        considered a subregion of the other
        """
        return self._get_float("LAYOUT_SUBREGION_THRESHOLD", 0.75)

    @property
    def ELEMENTS_H_PADDING_COEF(self) -> float:
        """When extending the boundaries of a PDF object for the purpose of determining which other
        elements should be considered in the same text region, we use a relative distance based on
        some fraction of the block height (typically character height). This is the fraction used
        for the horizontal extension applied to the left and right sides.
        """
        return self._get_float("ELEMENTS_H_PADDING_COEF", 0.4)

    @property
    def ELEMENTS_V_PADDING_COEF(self) -> float:
        """Same as ELEMENTS_H_PADDING_COEF but the vertical extension."""
        return self._get_float("ELEMENTS_V_PADDING_COEF", 0.3)

    @property
    def IMG_PROCESSOR_LONGEST_EDGE(self) -> int:
        """configuration for DetrImageProcessor to scale images"""
        return self._get_int("IMG_PROCESSOR_LONGEST_EDGE", 1333)

    @property
    def IMG_PROCESSOR_SHORTEST_EDGE(self) -> int:
        """configuration for DetrImageProcessor to scale images"""
        return self._get_int("IMG_PROCESSOR_SHORTEST_EDGE", 800)

    @property
    def PDF_ROTATION_DOMINANT_ANGLE_THRESHOLD(self) -> float:
        """minimum share of characters that must agree on a single 90-degree orientation
        before a rotated page's rendered image is re-oriented to make text upright

        Only consulted for pages with a non-zero ``/Rotate``. The fraction is intentionally
        high so that pages without a clear dominant text direction are left untouched.
        """
        return self._get_float("PDF_ROTATION_DOMINANT_ANGLE_THRESHOLD", 0.95)

    @property
    def PDF_RENDER_MAX_PIXELS_PER_PAGE(self) -> int:
        """maximum number of pixels (width * height) a single PDF page may render to

        Pages whose rendered bitmap would exceed this value are rejected before allocation.
        Set to 0 to disable the guard.
        """
        return self._get_int("PDF_RENDER_MAX_PIXELS_PER_PAGE", 1_000_000_000)


inference_config = InferenceConfig()
