import json
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from unstructured_inference.inference.elements import ImageTextRegion, TextRegion
from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.models.base import get_model
from unstructured_inference.models.detectron2onnx import (
    DEFAULT_LABEL_MAP as DETECTRON_LABEL_MAP,
)
from unstructured_inference.models.detectron2onnx import (
    UnstructuredDetectronONNXModel,
)
from unstructured_inference.models.yolox import YOLOX_LABEL_MAP, UnstructuredYoloXModel

from unstructured.documents.elements import Element, Text
from unstructured.partition.pdf_image.analysis.processor import AnalysisProcessor
from unstructured.partition.utils.sorting import coordinates_to_bbox


class LayoutDumper(ABC):
    layout_source: str = "unknown"

    @abstractmethod
    def dump(self) -> dict:
        """Transforms the results to a dict convertible structured formats like JSON or YAML"""


def extract_document_layout_info(layout: DocumentLayout) -> dict:
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


def object_detection_classes(model_name) -> List[str]:
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
        self.layout: dict = extract_document_layout_info(layout)
        self.model_name = model_name

    def dump(self) -> dict:
        """Transforms the results to COCO format and saves them to a file"""
        try:
            classes_dict = {"object_detection_classes": object_detection_classes(self.model_name)}
        except ValueError:
            classes_dict = {"object_detection_classes": []}
        self.layout.update(classes_dict)
        return self.layout


def _get_info_from_extracted_page(page: List[TextRegion]) -> List[dict]:
    elements = []
    for element in page:
        is_image = isinstance(element, ImageTextRegion)
        bbox = element.bbox
        elements.append(
            {
                "bbox": [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                "text": element.text,
                "source": str(element.source.value),
                "is_image": is_image,
            }
        )
    return elements


def extract_text_regions_info(layout: List[List[TextRegion]]) -> dict:
    pages = []
    for page_num, page in enumerate(layout, 1):
        elements = _get_info_from_extracted_page(page)
        pages.append({"number": page_num, "elements": elements})
    return {"pages": pages}


class ExtractedLayoutDumper(LayoutDumper):
    layout_source = "pdfminer"

    def __init__(self, layout: List[List[TextRegion]]):
        self.layout = extract_text_regions_info(layout)

    def dump(self) -> dict:
        return self.layout


class OCRLayoutDumper(LayoutDumper):
    layout_source = "ocr"

    def __init__(self):
        self.layout = []
        self.page_number = 1

    def add_ocred_page(self, page: List[TextRegion]):
        elements = _get_info_from_extracted_page(page)
        self.layout.append({"number": self.page_number, "elements": elements})
        self.page_number += 1

    def dump(self) -> dict:
        return {"pages": self.layout}


def _extract_final_element_info(element: Element) -> dict:
    element_type = (
        element.category if isinstance(element, Text) else str(element.__class__.__name__)
    )
    element_prob = getattr(element.metadata, "detection_class_prob", None)
    text = element.text
    bbox_points = coordinates_to_bbox(element.metadata.coordinates)
    cluster = getattr(element.metadata, "cluster", None)
    return {
        "type": element_type,
        "prob": element_prob,
        "text": text,
        "bbox": bbox_points,
        "cluster": cluster,
    }


def _extract_final_element_page_size(element: Element) -> dict:
    try:
        return {
            "width": element.metadata.coordinates.system.width,
            "height": element.metadata.coordinates.system.height,
        }
    except AttributeError:
        return {
            "width": None,
            "height": None,
        }


class FinalLayoutDumper(LayoutDumper):
    layout_source = "final"

    def __init__(self, layout: List[Element]):
        pages = defaultdict(list)
        for element in layout:
            element_page_number = element.metadata.page_number
            pages[element_page_number].append(_extract_final_element_info(element))
        extracted_pages = [
            {
                "number": page_number,
                "size": (
                    _extract_final_element_page_size(page_elements[0]) if page_elements else None
                ),
                "elements": page_elements,
            }
            for page_number, page_elements in pages.items()
        ]
        self.layout = {"pages": sorted(extracted_pages, key=lambda x: x["number"])}

    def dump(self) -> dict:
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
