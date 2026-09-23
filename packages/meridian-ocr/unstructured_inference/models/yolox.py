# Copyright (c) Megvii, Inc. and its affiliates.
# Unstructured modified the original source code found at:
# https://github.com/Megvii-BaseDetection/YOLOX/blob/237e943ac64aa32eb32f875faa93ebb18512d41d/yolox/data/data_augment.py
# https://github.com/Megvii-BaseDetection/YOLOX/blob/ac379df3c97d1835ebd319afad0c031c36d03f36/yolox/utils/demo_utils.py

import cv2
import numpy as np
import onnxruntime
from onnxruntime.capi import _pybind_state as C
from PIL import Image as PILImage

from unstructured_inference.constants import ElementType, Source
from unstructured_inference.inference.layoutelement import LayoutElements
from unstructured_inference.models.unstructuredmodel import (
    UnstructuredObjectDetectionModel,
)
from unstructured_inference.utils import (
    LazyDict,
    LazyEvaluateInfo,
    download_if_needed_and_get_local_path,
)

YOLOX_LABEL_MAP = {
    0: ElementType.CAPTION,
    1: ElementType.FOOTNOTE,
    2: ElementType.FORMULA,
    3: ElementType.LIST_ITEM,
    4: ElementType.PAGE_FOOTER,
    5: ElementType.PAGE_HEADER,
    6: ElementType.PICTURE,
    7: ElementType.SECTION_HEADER,
    8: ElementType.TABLE,
    9: ElementType.TEXT,
    10: ElementType.TITLE,
}

MODEL_TYPES = {
    "yolox": LazyDict(
        model_path=LazyEvaluateInfo(
            download_if_needed_and_get_local_path,
            "unstructuredio/yolo_x_layout",
            "yolox_l0.05.onnx",
        ),
        label_map=YOLOX_LABEL_MAP,
    ),
    "yolox_tiny": LazyDict(
        model_path=LazyEvaluateInfo(
            download_if_needed_and_get_local_path,
            "unstructuredio/yolo_x_layout",
            "yolox_tiny.onnx",
        ),
        label_map=YOLOX_LABEL_MAP,
    ),
    "yolox_quantized": LazyDict(
        model_path=LazyEvaluateInfo(
            download_if_needed_and_get_local_path,
            "unstructuredio/yolo_x_layout",
            "yolox_l0.05_quantized.onnx",
        ),
        label_map=YOLOX_LABEL_MAP,
    ),
}


class UnstructuredYoloXModel(UnstructuredObjectDetectionModel):
    def predict(self, x: PILImage.Image):
        """Predict using YoloX model."""
        super().predict(x)
        return self.image_processing(x)

    def initialize(self, model_path: str, label_map: dict):
        """Start inference session for YoloX model."""
        self.model_path = model_path

        available_providers = C.get_available_providers()
        ordered_providers = [
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        providers = [provider for provider in ordered_providers if provider in available_providers]

        self.model = onnxruntime.InferenceSession(
            model_path,
            providers=providers,
        )

        self.layout_classes = label_map

    def image_processing(
        self,
        image: PILImage.Image,
    ) -> LayoutElements:
        """Method runing YoloX for layout detection, returns a PageLayout
        parameters
        ----------
        page
            Path for image file with the image to process
        origin_img
            If specified, an Image object for process with YoloX model
        page_number
            Number asigned to the PageLayout returned
        output_directory
            Boolean indicating if result will be stored
        """
        # The model was trained and exported with this shape
        # TODO (benjamin): check other shapes for inference
        input_shape = (1024, 768)
        origin_img = np.array(image)
        image.close()
        img, ratio = preprocess(origin_img, input_shape)
        del origin_img  # Free full-size image array before ONNX inference
        session = self.model

        ort_inputs = {session.get_inputs()[0].name: img[None, :, :, :]}
        output = session.run(None, ort_inputs)
        del img, ort_inputs  # Free preprocessed inputs after inference
        # TODO(benjamin): check for p6
        predictions = demo_postprocess(output[0], input_shape, p6=False)[0]
        del output

        boxes = predictions[:, :4]
        scores = predictions[:, 4:5] * predictions[:, 5:]

        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.0
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.0
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.0
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.0
        boxes_xyxy /= ratio

        # Note (Benjamin): Distinct models (quantized and original) requires distincts
        # levels of thresholds
        if "quantized" in self.model_path:
            dets = multiclass_nms(boxes_xyxy, scores, nms_thr=0.0, score_thr=0.07)
        else:
            dets = multiclass_nms(boxes_xyxy, scores, nms_thr=0.1, score_thr=0.25)

        order = np.argsort(dets[:, 1])
        sorted_dets = dets[order]

        return LayoutElements(
            element_coords=sorted_dets[:, :4].astype(float),
            element_probs=sorted_dets[:, 4].astype(float),
            element_class_ids=sorted_dets[:, 5].astype(int),
            element_class_id_map=self.layout_classes,
            sources=np.array([Source.YOLOX] * sorted_dets.shape[0]),
        )


# Note: preprocess function was named preproc on original source


def preprocess(img, input_size, swap=(2, 0, 1)):
    """Preprocess image data before YoloX inference."""
    if len(img.shape) == 3:
        padded_img = np.full((input_size[0], input_size[1], 3), 114, dtype=np.uint8)
    else:
        padded_img = np.full(input_size, 114, dtype=np.uint8)

    r = min(input_size[0] / img.shape[0], input_size[1] / img.shape[1])
    resized_img = cv2.resize(
        img,
        (int(img.shape[1] * r), int(img.shape[0] * r)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.uint8)
    padded_img[: int(img.shape[0] * r), : int(img.shape[1] * r)] = resized_img

    padded_img = padded_img.transpose(swap)
    padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
    return padded_img, r


def demo_postprocess(outputs, img_size, p6=False):
    """Postprocessing for YoloX model."""
    grids = []
    expanded_strides = []

    strides = [8, 16, 32] if not p6 else [8, 16, 32, 64]

    hsizes = [img_size[0] // stride for stride in strides]
    wsizes = [img_size[1] // stride for stride in strides]

    for hsize, wsize, stride in zip(hsizes, wsizes, strides):
        xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
        grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
        grids.append(grid)
        shape = grid.shape[:2]
        expanded_strides.append(np.full((*shape, 1), stride))

    grids = np.concatenate(grids, 1)
    expanded_strides = np.concatenate(expanded_strides, 1)
    outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
    outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides

    return outputs


def multiclass_nms(boxes, scores, nms_thr, score_thr, class_agnostic=True):
    """Multiclass NMS implemented in Numpy"""
    # TODO(benjamin): check for non-class agnostic
    # if class_agnostic:
    nms_method = multiclass_nms_class_agnostic
    # else:
    #    nms_method = multiclass_nms_class_aware
    return nms_method(boxes, scores, nms_thr, score_thr)


def multiclass_nms_class_agnostic(boxes, scores, nms_thr, score_thr):
    """Multiclass NMS implemented in Numpy. Class-agnostic version."""
    cls_inds = scores.argmax(1)
    cls_scores = scores[np.arange(len(cls_inds)), cls_inds]

    valid_score_mask = cls_scores > score_thr
    valid_scores = cls_scores[valid_score_mask]
    valid_boxes = boxes[valid_score_mask]
    valid_cls_inds = cls_inds[valid_score_mask]
    keep = nms(valid_boxes, valid_scores, nms_thr)
    dets = np.concatenate(
        [valid_boxes[keep], valid_scores[keep, None], valid_cls_inds[keep, None]],
        1,
    )
    return dets


def nms(boxes, scores, nms_thr):
    """Single class NMS implemented in Numpy."""
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= nms_thr)[0]
        order = order[inds + 1]

    return keep
