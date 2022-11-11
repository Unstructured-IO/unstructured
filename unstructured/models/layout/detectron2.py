import sys

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from layoutparser.models.detectron2.layoutmodel import (
    is_detectron2_available,
    Detectron2LayoutModel,
)

from unstructured.logger import get_logger

logger = get_logger()

model: Detectron2LayoutModel = None

DETECTRON_CONFIG: Final = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"


def load_model():
    """Loads the detectron2 model as a global variable to ensure that we are not loading
    it multiple times."""
    global model

    if not is_detectron2_available():
        raise ImportError(
            "Failed to load the Detectron2 model. Ensure that the Detectron2 "
            "module is correctly installed."
        )

    if model is None:
        logger.info("Loading the Detectron2 layout model ...")
        model = Detectron2LayoutModel(
            DETECTRON_CONFIG,
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
            label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
        )
