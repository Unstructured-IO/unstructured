# https://github.com/microsoft/table-transformer/blob/main/src/inference.py
# https://github.com/NielsRogge/Transformers-Tutorials/blob/master/Table%20Transformer/Using_Table_Transformer_for_table_detection_and_table_structure_recognition.ipynb
import threading
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import cv2
import numpy as np
import torch
from PIL import Image as PILImage
from transformers import DetrImageProcessor, TableTransformerForObjectDetection, logging
from transformers.models.table_transformer.modeling_table_transformer import (
    TableTransformerObjectDetectionOutput,
)

from unstructured_inference.config import inference_config
from unstructured_inference.inference.layoutelement import table_cells_to_dataframe
from unstructured_inference.logger import logger
from unstructured_inference.models.table_postprocess import Rect
from unstructured_inference.models.unstructuredmodel import UnstructuredModel
from unstructured_inference.utils import pad_image_with_background_color

from . import table_postprocess as postprocess

DEFAULT_MODEL = "microsoft/table-transformer-structure-recognition"


class UnstructuredTableTransformerModel(UnstructuredModel):
    """Unstructured model wrapper for table-transformer."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """return an instance if one already exists otherwise create an instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UnstructuredTableTransformerModel, cls).__new__(cls)
        return cls._instance

    def predict(
        self,
        x: PILImage.Image,
        ocr_tokens: Optional[List[Dict]] = None,
        result_format: str = "html",
    ):
        """Predict table structure deferring to run_prediction with ocr tokens

        Note:
        `ocr_tokens` is a list of dictionaries representing OCR tokens,
        where each dictionary has the following format:
        {
            "bbox": [int, int, int, int],  # Bounding box coordinates of the token
            "block_num": int,  # Block number
            "line_num": int,   # Line number
            "span_num": int,   # Span number
            "text": str,  # Text content of the token
        }
        The bounding box coordinates should match the table structure.
        FIXME: refactor token data into a dataclass so we have clear expectations of the fields
        """
        super().predict(x)
        return self.run_prediction(x, ocr_tokens=ocr_tokens, result_format=result_format)

    def initialize(
        self,
        model: Union[str, Path],
        device: Optional[str] = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """Loads the table transformer model using the specified parameters.

        Device placement strategy:
        - Normalize device names (cuda -> cuda:0) for consistent caching
        - Load models WITHOUT device_map to avoid meta tensor errors
        - Use explicit .to(device, dtype=torch.float32) for proper placement
        """
        # Device normalization for consistent caching
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device.startswith("cuda") and ":" not in device:
            if torch.cuda.is_available():
                device = f"cuda:{torch.cuda.current_device()}"
            else:
                logger.warning("CUDA device requested but not available, falling back to CPU")
                device = "cpu"

        self.device = device

        # Load feature extractor WITHOUT device_map
        self.feature_extractor = DetrImageProcessor.from_pretrained(model)
        # value not set in the configuration and needed for newer models
        # https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-all/discussions/1
        self.feature_extractor.size["shortest_edge"] = inference_config.IMG_PROCESSOR_SHORTEST_EDGE
        self.feature_extractor.size["longest_edge"] = inference_config.IMG_PROCESSOR_LONGEST_EDGE

        try:
            logger.info(f"Loading table structure model to {self.device}...")
            cached_current_verbosity = logging.get_verbosity()
            logging.set_verbosity_error()

            # Load model WITHOUT device_map (prevents meta tensor errors)
            self.model = TableTransformerForObjectDetection.from_pretrained(model)

            # Explicit device placement with dtype
            # NOTE: While nn.Module.to() modifies in-place, capturing return value is
            # recommended best practice per PyTorch docs for consistency and clarity
            self.model = self.model.to(self.device, dtype=torch.float32)

            logging.set_verbosity(cached_current_verbosity)
            self.model.eval()
            logger.info(f"Table model successfully loaded to {self.device}")

        except EnvironmentError:
            logger.critical("Failed to initialize the model.")
            logger.critical("Ensure that the model is correct")
            raise ImportError(
                "Review the parameters to initialize a UnstructuredTableTransformerModel obj",
            )

    def get_structure(
        self,
        x: PILImage.Image,
        pad_for_structure_detection: int = inference_config.TABLE_IMAGE_BACKGROUND_PAD,
    ) -> TableTransformerObjectDetectionOutput:
        """get the table structure as a dictionary contaning different types of elements as
        key-value pairs; check table-transformer documentation for more information"""
        with torch.no_grad():
            encoding = self.feature_extractor(
                pad_image_with_background_color(x, pad_for_structure_detection),
                return_tensors="pt",
            ).to(self.device)
            outputs_structure = self.model(**encoding)
            outputs_structure["pad_for_structure_detection"] = pad_for_structure_detection
            return outputs_structure

    def run_prediction(
        self,
        x: PILImage.Image,
        pad_for_structure_detection: int = inference_config.TABLE_IMAGE_BACKGROUND_PAD,
        ocr_tokens: Optional[List[Dict]] = None,
        result_format: Optional[str] = "html",
    ):
        """Predict table structure"""
        outputs_structure = self.get_structure(x, pad_for_structure_detection)
        if ocr_tokens is None:
            raise ValueError("Cannot predict table structure with no OCR tokens")

        recognized_table = recognize(outputs_structure, x, tokens=ocr_tokens)
        if len(recognized_table) > 0:
            prediction = recognized_table[0]
        # NOTE(robinson) - This means that the table was not recognized
        else:
            return ""

        if result_format == "html":
            # Convert cells to HTML
            prediction = cells_to_html(prediction) or ""
        elif result_format == "dataframe":
            prediction = table_cells_to_dataframe(prediction)
        elif result_format == "cells":
            prediction = prediction
        else:
            raise ValueError(
                f"result_format {result_format} is not a valid format. "
                f'Valid formats are: "html", "dataframe", "cells"',
            )

        return prediction


tables_agent: UnstructuredTableTransformerModel = UnstructuredTableTransformerModel()


def load_agent():
    """Loads the Table agent."""

    if getattr(tables_agent, "model", None) is None:
        with tables_agent._lock:
            if getattr(tables_agent, "model", None) is None:
                logger.info("Loading the Table agent ...")
                tables_agent.initialize(DEFAULT_MODEL)

    return


def get_class_map(data_type: str):
    """Defines class map dictionaries"""
    if data_type == "structure":
        class_map = {
            "table": 0,
            "table column": 1,
            "table row": 2,
            "table column header": 3,
            "table projected row header": 4,
            "table spanning cell": 5,
            "no object": 6,
        }
    elif data_type == "detection":
        class_map = {"table": 0, "table rotated": 1, "no object": 2}
    return class_map


structure_class_thresholds = {
    "table": inference_config.TT_TABLE_CONF,
    "table column": inference_config.TABLE_COLUMN_CONF,
    "table row": inference_config.TABLE_ROW_CONF,
    "table column header": inference_config.TABLE_COLUMN_HEADER_CONF,
    "table projected row header": inference_config.TABLE_PROJECTED_ROW_HEADER_CONF,
    "table spanning cell": inference_config.TABLE_SPANNING_CELL_CONF,
    # FIXME (yao) this parameter doesn't seem to be used at all in inference? Can we remove it
    "no object": 10,
}


def recognize(outputs: TableTransformerObjectDetectionOutput, img: PILImage.Image, tokens: list):
    """Recognize table elements."""
    str_class_name2idx = get_class_map("structure")
    str_class_idx2name = {v: k for k, v in str_class_name2idx.items()}
    class_thresholds = structure_class_thresholds

    # Post-process detected objects, assign class labels
    objects = outputs_to_objects(outputs, img.size, str_class_idx2name)
    high_confidence_objects = apply_thresholds_on_objects(objects, class_thresholds)
    # Further process the detected objects so they correspond to a consistent table
    tables_structure = objects_to_structures(high_confidence_objects, tokens, class_thresholds)
    # Enumerate all table cells: grid cells and spanning cells
    return [structure_to_cells(structure, tokens)[0] for structure in tables_structure]


def outputs_to_objects(
    outputs: TableTransformerObjectDetectionOutput,
    img_size: Tuple[int, int],
    class_idx2name: Mapping[int, str],
):
    """Output table element types."""
    m = outputs["logits"].softmax(-1).max(-1)
    pred_labels = m.indices.detach().cpu().numpy()[0]
    pred_scores = m.values.detach().cpu().numpy()[0]
    pred_bboxes = outputs["pred_boxes"].detach().cpu()[0]

    pad = outputs.get("pad_for_structure_detection", 0)
    scale_size = (img_size[0] + pad * 2, img_size[1] + pad * 2)
    rescaled = rescale_bboxes(pred_bboxes, scale_size)
    # unshift the padding; padding effectively shifted the bounding boxes of structures in the
    # original image with half of the total pad
    if pad != 0:
        rescaled = rescaled - pad
    pred_bboxes = rescaled.tolist()

    objects = []
    for label, score, bbox in zip(pred_labels, pred_scores, pred_bboxes):
        class_label = class_idx2name[int(label)]
        if class_label != "no object":
            objects.append(
                {
                    "label": class_label,
                    "score": float(score),
                    "bbox": bbox,
                },
            )

    return objects


def apply_thresholds_on_objects(
    objects: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, float],
) -> Sequence[Mapping[str, Any]]:
    """
    Filters predicted objects which the confidence scores below the thresholds

    Args:
        objects: Sequence of mappings for example:
        [
            {
                "label": "table row",
                "score": 0.55,
                "bbox": [...],
            },
            ...,
        ]
        thresholds: Mapping from labels to thresholds

    Returns:
        Filtered list of objects

    """
    objects = [obj for obj in objects if obj["score"] >= thresholds[obj["label"]]]
    return objects


# for output bounding box post-processing
def box_cxcywh_to_xyxy(x):
    """Convert rectangle format from center-x, center-y, width, height to
    x-min, y-min, x-max, y-max."""
    x_c, y_c, w, h = x.unbind(-1)
    b = [(x_c - 0.5 * w), (y_c - 0.5 * h), (x_c + 0.5 * w), (y_c + 0.5 * h)]
    return torch.stack(b, dim=1)


def rescale_bboxes(out_bbox, size):
    """Rescale relative bounding box to box of size given by size."""
    img_w, img_h = size
    b = box_cxcywh_to_xyxy(out_bbox)
    b = b * torch.tensor([img_w, img_h, img_w, img_h], dtype=torch.float32, device=out_bbox.device)
    return b


def iob(bbox1, bbox2):
    """
    Compute the intersection area over box area, for bbox1.
    """
    intersection = Rect(bbox1).intersect(Rect(bbox2))

    bbox1_area = Rect(bbox1).get_area()
    if bbox1_area > 0:
        return intersection.get_area() / bbox1_area

    return 0


def objects_to_structures(objects, tokens, class_thresholds):
    """
    Process the bounding boxes produced by the table structure recognition model into
    a *consistent* set of table structures (rows, columns, spanning cells, headers).
    This entails resolving conflicts/overlaps, and ensuring the boxes meet certain alignment
    conditions (for example: rows should all have the same width, etc.).
    """

    tables = [obj for obj in objects if obj["label"] == "table"]
    table_structures = []

    for table in tables:
        table_objects = [
            obj
            for obj in objects
            if iob(obj["bbox"], table["bbox"]) >= inference_config.TABLE_IOB_THRESHOLD
        ]
        table_tokens = [
            token
            for token in tokens
            if iob(token["bbox"], table["bbox"]) >= inference_config.TABLE_IOB_THRESHOLD
        ]

        structure = {}

        columns = [obj for obj in table_objects if obj["label"] == "table column"]
        rows = [obj for obj in table_objects if obj["label"] == "table row"]
        column_headers = [obj for obj in table_objects if obj["label"] == "table column header"]
        spanning_cells = [obj for obj in table_objects if obj["label"] == "table spanning cell"]
        for obj in spanning_cells:
            obj["projected row header"] = False
        projected_row_headers = [
            obj for obj in table_objects if obj["label"] == "table projected row header"
        ]
        for obj in projected_row_headers:
            obj["projected row header"] = True
        spanning_cells += projected_row_headers
        for obj in rows:
            obj["column header"] = False
            for header_obj in column_headers:
                if iob(obj["bbox"], header_obj["bbox"]) >= inference_config.TABLE_IOB_THRESHOLD:
                    obj["column header"] = True

        # Refine table structures
        rows = postprocess.refine_rows(rows, table_tokens, class_thresholds["table row"])
        columns = postprocess.refine_columns(
            columns,
            table_tokens,
            class_thresholds["table column"],
        )

        # Shrink table bbox to just the total height of the rows
        # and the total width of the columns
        row_rect = Rect()
        for obj in rows:
            row_rect.include_rect(obj["bbox"])
        column_rect = Rect()
        for obj in columns:
            column_rect.include_rect(obj["bbox"])
        table["row_column_bbox"] = [
            column_rect.x_min,
            row_rect.y_min,
            column_rect.x_max,
            row_rect.y_max,
        ]
        table["bbox"] = table["row_column_bbox"]

        # Process the rows and columns into a complete segmented table
        columns = postprocess.align_columns(columns, table["row_column_bbox"])
        rows = postprocess.align_rows(rows, table["row_column_bbox"])

        structure["rows"] = rows
        structure["columns"] = columns
        structure["column headers"] = column_headers
        structure["spanning cells"] = spanning_cells

        if len(rows) > 0 and len(columns) > 1:
            structure = refine_table_structure(structure, class_thresholds)

        table_structures.append(structure)

    return table_structures


def refine_table_structure(table_structure, class_thresholds):
    """
    Apply operations to the detected table structure objects such as
    thresholding, NMS, and alignment.
    """
    rows = table_structure["rows"]
    columns = table_structure["columns"]

    # Process the headers
    column_headers = table_structure["column headers"]
    column_headers = postprocess.apply_threshold(
        column_headers,
        class_thresholds["table column header"],
    )
    column_headers = postprocess.nms(column_headers)
    column_headers = align_headers(column_headers, rows)

    # Process spanning cells
    spanning_cells = [
        elem for elem in table_structure["spanning cells"] if not elem["projected row header"]
    ]
    projected_row_headers = [
        elem for elem in table_structure["spanning cells"] if elem["projected row header"]
    ]
    spanning_cells = postprocess.apply_threshold(
        spanning_cells,
        class_thresholds["table spanning cell"],
    )
    projected_row_headers = postprocess.apply_threshold(
        projected_row_headers,
        class_thresholds["table projected row header"],
    )
    spanning_cells += projected_row_headers
    # Align before NMS for spanning cells because alignment brings them into agreement
    # with rows and columns first; if spanning cells still overlap after this operation,
    # the threshold for NMS can basically be lowered to just above 0
    spanning_cells = postprocess.align_supercells(spanning_cells, rows, columns)
    spanning_cells = postprocess.nms_supercells(spanning_cells)

    postprocess.header_supercell_tree(spanning_cells)

    table_structure["columns"] = columns
    table_structure["rows"] = rows
    table_structure["spanning cells"] = spanning_cells
    table_structure["column headers"] = column_headers

    return table_structure


def align_headers(headers, rows):
    """
    Adjust the header boundary to be the convex hull of the rows it intersects
    at least 50% of the height of.

    For now, we are not supporting tables with multiple headers, so we need to
    eliminate anything besides the top-most header.
    """

    aligned_headers = []

    for row in rows:
        row["column header"] = False

    header_row_nums = []
    for header in headers:
        for row_num, row in enumerate(rows):
            row_height = row["bbox"][3] - row["bbox"][1]
            min_row_overlap = max(row["bbox"][1], header["bbox"][1])
            max_row_overlap = min(row["bbox"][3], header["bbox"][3])
            overlap_height = max_row_overlap - min_row_overlap
            if overlap_height / row_height >= 0.5:
                header_row_nums.append(row_num)

    if len(header_row_nums) == 0:
        return aligned_headers

    header_rect = Rect()
    if header_row_nums[0] > 0:
        header_row_nums = list(range(header_row_nums[0] + 1)) + header_row_nums

    last_row_num = -1
    for row_num in header_row_nums:
        if row_num == last_row_num + 1:
            row = rows[row_num]
            row["column header"] = True
            header_rect = header_rect.include_rect(row["bbox"])
            last_row_num = row_num
        else:
            # Break as soon as a non-header row is encountered.
            # This ignores any subsequent rows in the table labeled as a header.
            # Having more than 1 header is not supported currently.
            break

    header = {"bbox": header_rect.get_bbox()}
    aligned_headers.append(header)

    return aligned_headers


def compute_confidence_score(cell_match_scores):
    """
    Compute a confidence score based on how well the page tokens
    slot into the cells reported by the model
    """
    try:
        mean_match_score = sum(cell_match_scores) / len(cell_match_scores)
        min_match_score = min(cell_match_scores)
        confidence_score = (mean_match_score + min_match_score) / 2
    except ZeroDivisionError:
        confidence_score = 0
    return confidence_score


def structure_to_cells(table_structure, tokens):
    """
    Assuming the row, column, spanning cell, and header bounding boxes have
    been refined into a set of consistent table structures, process these
    table structures into table cells. This is a universal representation
    format for the table, which can later be exported to Pandas or CSV formats.
    Classify the cells as header/access cells or data cells
    based on if they intersect with the header bounding box.
    """
    columns = table_structure["columns"]
    rows = table_structure["rows"]
    spanning_cells = table_structure["spanning cells"]
    spanning_cells = sorted(spanning_cells, reverse=True, key=lambda cell: cell["score"])

    cells = []
    subcells = []
    # Identify complete cells and subcells
    for column_num, column in enumerate(columns):
        for row_num, row in enumerate(rows):
            column_rect = Rect(list(column["bbox"]))
            row_rect = Rect(list(row["bbox"]))
            cell_rect = row_rect.intersect(column_rect)
            header = "column header" in row and row["column header"]
            cell = {
                "bbox": cell_rect.get_bbox(),
                "column_nums": [column_num],
                "row_nums": [row_num],
                "column header": header,
            }

            cell["subcell"] = False
            for spanning_cell in spanning_cells:
                spanning_cell_rect = Rect(list(spanning_cell["bbox"]))
                if (
                    spanning_cell_rect.intersect(cell_rect).get_area() / cell_rect.get_area()
                ) > inference_config.TABLE_IOB_THRESHOLD:
                    cell["subcell"] = True
                    cell["is_merged"] = False
                    break

            if cell["subcell"]:
                subcells.append(cell)
            else:
                # cell text = extract_text_inside_bbox(table_spans, cell['bbox'])
                # cell['cell text'] = cell text
                cell["projected row header"] = False
                cells.append(cell)

    for spanning_cell in spanning_cells:
        spanning_cell_rect = Rect(list(spanning_cell["bbox"]))
        cell_columns = set()
        cell_rows = set()
        cell_rect = None
        header = True
        for subcell in subcells:
            subcell_rect = Rect(list(subcell["bbox"]))
            subcell_rect_area = subcell_rect.get_area()
            if (
                subcell_rect.intersect(spanning_cell_rect).get_area() / subcell_rect_area
            ) > inference_config.TABLE_IOB_THRESHOLD and subcell["is_merged"] is False:
                if cell_rect is None:
                    cell_rect = Rect(list(subcell["bbox"]))
                else:
                    cell_rect.include_rect(list(subcell["bbox"]))
                cell_rows = cell_rows.union(set(subcell["row_nums"]))
                cell_columns = cell_columns.union(set(subcell["column_nums"]))
                # By convention here, all subcells must be classified
                # as header cells for a spanning cell to be classified as a header cell;
                # otherwise, this could lead to a non-rectangular header region
                header = header and "column header" in subcell and subcell["column header"]
                subcell["is_merged"] = True

        if len(cell_rows) > 0 and len(cell_columns) > 0:
            cell = {
                "bbox": cell_rect.get_bbox(),
                "column_nums": list(cell_columns),
                "row_nums": list(cell_rows),
                "column header": header,
                "projected row header": spanning_cell["projected row header"],
            }
            cells.append(cell)

    _, _, cell_match_scores = postprocess.slot_into_containers(cells, tokens)
    confidence_score = compute_confidence_score(cell_match_scores)

    # Dilate rows and columns before final extraction
    # dilated_columns = fill_column_gaps(columns, table_bbox)
    dilated_columns = columns
    # dilated_rows = fill_row_gaps(rows, table_bbox)
    dilated_rows = rows
    for cell in cells:
        column_rect = Rect()
        for column_num in cell["column_nums"]:
            column_rect.include_rect(list(dilated_columns[column_num]["bbox"]))
        row_rect = Rect()
        for row_num in cell["row_nums"]:
            row_rect.include_rect(list(dilated_rows[row_num]["bbox"]))
        cell_rect = column_rect.intersect(row_rect)
        cell["bbox"] = cell_rect.get_bbox()

    span_nums_by_cell, _, _ = postprocess.slot_into_containers(
        cells,
        tokens,
        overlap_threshold=0.001,
        forced_assignment=False,
    )

    for cell, cell_span_nums in zip(cells, span_nums_by_cell):
        cell_spans = [tokens[num] for num in cell_span_nums]
        # TODO: Refine how text is extracted; should be character-based, not span-based;
        # but need to associate
        cell["cell text"] = postprocess.extract_text_from_spans(
            cell_spans,
            remove_integer_superscripts=False,
        )
        cell["spans"] = cell_spans

    # Adjust the row, column, and cell bounding boxes to reflect the extracted text
    num_rows = len(rows)
    rows = postprocess.sort_objects_top_to_bottom(rows)
    num_columns = len(columns)
    columns = postprocess.sort_objects_left_to_right(columns)
    min_y_values_by_row = defaultdict(list)
    max_y_values_by_row = defaultdict(list)
    min_x_values_by_column = defaultdict(list)
    max_x_values_by_column = defaultdict(list)
    for cell in cells:
        min_row = min(cell["row_nums"])
        max_row = max(cell["row_nums"])
        min_column = min(cell["column_nums"])
        max_column = max(cell["column_nums"])
        for span in cell["spans"]:
            min_x_values_by_column[min_column].append(span["bbox"][0])
            min_y_values_by_row[min_row].append(span["bbox"][1])
            max_x_values_by_column[max_column].append(span["bbox"][2])
            max_y_values_by_row[max_row].append(span["bbox"][3])
    for row_num, row in enumerate(rows):
        if len(min_x_values_by_column[0]) > 0:
            row["bbox"][0] = min(min_x_values_by_column[0])
        if len(min_y_values_by_row[row_num]) > 0:
            row["bbox"][1] = min(min_y_values_by_row[row_num])
        if len(max_x_values_by_column[num_columns - 1]) > 0:
            row["bbox"][2] = max(max_x_values_by_column[num_columns - 1])
        if len(max_y_values_by_row[row_num]) > 0:
            row["bbox"][3] = max(max_y_values_by_row[row_num])
    for column_num, column in enumerate(columns):
        if len(min_x_values_by_column[column_num]) > 0:
            column["bbox"][0] = min(min_x_values_by_column[column_num])
        if len(min_y_values_by_row[0]) > 0:
            column["bbox"][1] = min(min_y_values_by_row[0])
        if len(max_x_values_by_column[column_num]) > 0:
            column["bbox"][2] = max(max_x_values_by_column[column_num])
        if len(max_y_values_by_row[num_rows - 1]) > 0:
            column["bbox"][3] = max(max_y_values_by_row[num_rows - 1])
    for cell in cells:
        row_rect = None
        column_rect = None
        for row_num in cell["row_nums"]:
            if row_rect is None:
                row_rect = Rect(list(rows[row_num]["bbox"]))
            else:
                row_rect.include_rect(list(rows[row_num]["bbox"]))
        for column_num in cell["column_nums"]:
            if column_rect is None:
                column_rect = Rect(list(columns[column_num]["bbox"]))
            else:
                column_rect.include_rect(list(columns[column_num]["bbox"]))
        cell_rect = row_rect.intersect(column_rect)
        if cell_rect.get_area() > 0:
            cell["bbox"] = cell_rect.get_bbox()
            pass

    return cells, confidence_score


def fill_cells(cells: List[dict]) -> List[dict]:
    """fills the missing cells in the table by adding a cells with empty text
    where there are no cells detected by the model.

    A cell contains the following keys relevent to the html conversion:
    row_nums: List[int]
        the row numbers this cell belongs to; for cells spanning multiple rows there are more than
        one numbers
    column_nums: List[int]
        the columns numbers this cell belongs to; for cells spanning multiple columns there are more
        than one numbers
    cell text: str
        the text in this cell
    column header: bool
        whether this cell is a column header

    """
    if not cells:
        return []

    # Find max row and col indices
    max_row = max(row for cell in cells for row in cell["row_nums"])
    max_col = max(col for cell in cells for col in cell["column_nums"])
    filled = set()
    for cell in cells:
        for row in cell["row_nums"]:
            for col in cell["column_nums"]:
                filled.add((row, col))
    header_rows = set()
    for cell in cells:
        if cell["column header"]:
            header_rows.update(cell["row_nums"])

    # Compose output list directly for speed
    new_cells = cells.copy()
    for row in range(max_row + 1):
        for col in range(max_col + 1):
            if (row, col) not in filled:
                new_cells.append(
                    {
                        "row_nums": [row],
                        "column_nums": [col],
                        "cell text": "",
                        "column header": row in header_rows,
                    }
                )
    return new_cells


def cells_to_html(cells: List[dict]) -> str:
    """Convert table structure to html format.

    Args:
        cells: List of dictionaries representing table cells, where each dictionary has the
            following format:
            {
                "row_nums": List[int],
                "column_nums": List[int],
                "cell text": str,
                "column header": bool,
            }
    Returns:
        str: HTML table string
    """
    # Pre-sort with tuple key, as per original
    cells_filled = fill_cells(cells)
    cells_sorted = sorted(cells_filled, key=lambda k: (min(k["row_nums"]), min(k["column_nums"])))

    table = ET.Element("table")
    current_row = -1

    # Check if any column header exists
    table_has_header = any(cell["column header"] for cell in cells_sorted)
    table_header = ET.SubElement(table, "thead") if table_has_header else None
    table_body = ET.SubElement(table, "tbody")

    row = None
    for cell in cells_sorted:
        this_row = min(cell["row_nums"])
        attrib = {}
        colspan = len(cell["column_nums"])
        if colspan > 1:
            attrib["colspan"] = str(colspan)
        rowspan = len(cell["row_nums"])
        if rowspan > 1:
            attrib["rowspan"] = str(rowspan)
        if this_row > current_row:
            current_row = this_row
            if cell["column header"]:
                table_subelement = table_header
                cell_tag = "th"
            else:
                table_subelement = table_body
                cell_tag = "td"
            row = ET.SubElement(table_subelement, "tr")  # type: ignore
        if row is not None:
            tcell = ET.SubElement(row, cell_tag, attrib=attrib)
            tcell.text = cell["cell text"]

    return str(ET.tostring(table, encoding="unicode", short_empty_elements=False))


def zoom_image(image: PILImage.Image, zoom: float) -> PILImage.Image:
    """scale an image based on the zoom factor using cv2; the scaled image is post processed by
    dilation then erosion to improve edge sharpness for OCR tasks"""
    if zoom <= 0:
        # no zoom but still does dilation and erosion
        zoom = 1
    new_image = cv2.resize(
        cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR),
        None,
        fx=zoom,
        fy=zoom,
        interpolation=cv2.INTER_CUBIC,
    )
    kernel = np.ones((1, 1), np.uint8)
    new_image = cv2.dilate(new_image, kernel, iterations=1, dst=new_image)
    new_image = cv2.erode(new_image, kernel, iterations=1, dst=new_image)

    return PILImage.fromarray(new_image)
