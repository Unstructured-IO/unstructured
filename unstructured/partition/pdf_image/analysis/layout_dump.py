import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.models.base import get_model
from unstructured_inference.models.detectron2onnx import (
    DEFAULT_LABEL_MAP as DETECTRON_LABEL_MAP,
)
from unstructured_inference.models.detectron2onnx import (
    UnstructuredDetectronONNXModel,
)
from unstructured_inference.models.yolox import YOLOX_LABEL_MAP, UnstructuredYoloXModel

from unstructured.partition.pdf_image.analysis.processor import AnalysisProcessor


class LayoutDumper(ABC):
    layout_source: str = "unknown"

    @abstractmethod
    def dump(self) -> dict:
        """Transforms the results to a dict convertible structured formats like JSON or YAML"""


def extract_layout_info(layout: DocumentLayout) -> dict:
    pages = []

    for page in layout.pages:
        size = {
            "width": page.image_metadata.get("width"),
            "height": page.image_metadata.get("height"),
        }
        elements = []
        for element in page.elements:
            bbox = element.bbox
            elements.append(
                {
                    "bbox": [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                    "type": element.type,
                    "prob": element.prob,
                }
            )
        pages.append({"number": page.number, "size": size, "elements": elements})
    return {"pages": pages}


def object_detection_classes(model_name) -> list[str]:
    model = get_model(model_name)
    if isinstance(model, UnstructuredYoloXModel):
        return list(YOLOX_LABEL_MAP.values())
    if isinstance(model, UnstructuredDetectronONNXModel):
        return list(DETECTRON_LABEL_MAP.values())
    else:
        raise ValueError(f"Cannot get OD model classes - unknown model type: {model_name}")


class ObjectDetectionLayoutDumper(LayoutDumper):
    """Forms the results in COCO format and saves them to a file"""

    layout_source = "object_detection"

    def __init__(self, layout: DocumentLayout, model_name: Optional[str] = None):
        self.layout: dict = extract_layout_info(layout)
        self.model_name = model_name

    def dump(self) -> dict:
        """Transforms the results to COCO format and saves them to a file"""
        try:
            classes_dict = {"object_detection_classes": object_detection_classes(self.model_name)}
        except ValueError:
            classes_dict = {"object_detection_classes": []}
        self.layout.update(classes_dict)
        return self.layout


class JsonLayoutDumper(AnalysisProcessor):
    """Dumps the results of the analysis to a JSON file"""

    def __init__(self, filename: str, save_dir: str):
        self.dumpers = []
        super().__init__(filename, save_dir)

    def add_layout_dumper(self, dumper: LayoutDumper):
        self.dumpers.append(dumper)

    def process(self):
        filename_stem = Path(self.filename).stem
        analysis_save_dir = Path(self.save_dir) / "analysis" / filename_stem / "layout_dump"
        analysis_save_dir.mkdir(parents=True, exist_ok=True)
        for dumper in self.dumpers:
            results = dumper.dump()
            with open(analysis_save_dir / f"{dumper.layout_source}.json", "w") as f:
                f.write(json.dumps(results, indent=2))
