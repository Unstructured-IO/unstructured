"""
Implements object detection metrics: average precision, precision, recall, and f1 score.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

IOU_THRESHOLDS = torch.tensor(
    [0.5000, 0.5500, 0.6000, 0.6500, 0.7000, 0.7500, 0.8000, 0.8500, 0.9000, 0.9500]
)
SCORE_THRESHOLD = 0.1
RECALL_THRESHOLDS = torch.arange(0, 1.01, 0.01)


@dataclass
class ObjectDetectionEvaluation:
    """Class representing a gathered table metrics."""

    f1_score: float
    precision: float
    recall: float
    m_ap: float


class ObjectDetectionEvalProcessor:

    iou_thresholds = IOU_THRESHOLDS
    score_threshold = SCORE_THRESHOLD
    recall_thresholds = RECALL_THRESHOLDS

    def __init__(
        self,
        document_preds: list[torch.Tensor],
        document_targets: list[torch.Tensor],
        pages_height: list[int],
        pages_width: list[int],
        class_labels: list[str],
        device: str = "cpu",
    ):
        """
        Initializes the ObjectDetection prediction and ground truth.

        Args:
            document_preds (list):      list (of length pages of document) of
                                        Tensors of shape (num_predictions, 6)
                                        format: (x1, y1, x2, y2, confidence,class_label)
                                        where x1,y1,x2,y2 are according to image size
            document_targets (list):    list (of length pages of document) of
                                        Tensors of shape (num_targets, 6)
                                        format: (label, x1, y1, x2, y2)
                                        where x,y,w,h are according to image size
            pages_height (list):        list of height of each page in the document
            pages_width (list):         list of width of each page in the document
            class_labels (list):        list of class labels
        """
        self.device = device
        self.document_preds = [pred.to(device) for pred in document_preds]
        self.document_targets = [target.to(device) for target in document_targets]
        self.pages_height = pages_height
        self.pages_width = pages_width
        self.num_cls = len(class_labels)

    @classmethod
    def from_json_files(
        cls,
        prediction_file_path: Path,
        ground_truth_file_path: Path,
    ) -> "ObjectDetectionEvalProcessor":
        """
        Initializes the ObjectDetection prediction and ground truth,
        and converts the data to the required format.

        Args:
            prediction_file_path (Path): path to json file with predictions dump from OD model
            ground_truth_file_path (Path): path to json file with OD ground truth data
        """
        # TODO: Test after https://unstructured-ai.atlassian.net/browse/ML-92
        # is done.
        with open(prediction_file_path) as f:
            predictions_data = json.load(f)
        with open(ground_truth_file_path) as f:
            ground_truth_data = json.load(f)

        assert (
            predictions_data["object_detection_classes"]
            == ground_truth_data["object_detection_classes"]
        ), "Classes in predictions and ground truth do not match."
        assert len(predictions_data["pages"]) == len(
            ground_truth_data["pages"]
        ), "Pages number in predictions and ground truth do not match."
        for pred_page, gt_page in zip(predictions_data["pages"], ground_truth_data["pages"]):
            assert (
                pred_page["size"] == gt_page["size"]
            ), "Page sizes in predictions and ground truth do not match."

        class_labels = predictions_data["object_detection_classes"]
        document_preds = cls._process_data(predictions_data, class_labels, prediction=True)
        document_targets = cls._process_data(ground_truth_data, class_labels)
        pages_height, pages_width = cls._parse_page_dimensions(predictions_data)

        return cls(document_preds, document_targets, pages_height, pages_width, class_labels)

    @staticmethod
    def _parse_page_dimensions(data: dict) -> tuple[list, list]:
        """
        Process the page dimensions from the json file to the required format.
        """
        pages_height = []
        pages_width = []
        for page in data["pages"]:
            pages_height.append(page["size"]["height"])
            pages_width.append(page["size"]["width"])
        return pages_height, pages_width

    @staticmethod
    def _process_data(data: dict, class_labels, prediction: bool = False) -> list[dict]:
        """
        Process the elements from the json file to the required format.
        """
        pages_list = []
        for page in data["pages"]:
            page_elements = []
            for element in page["elements"]:
                # Extract coordinates, confidence, and class label from each prediction
                class_label = element["type"]
                class_idx = class_labels.index(class_label)
                x1, y1, x2, y2 = element["bbox"]
                if prediction:
                    confidence = element["prob"]
                    page_elements.append([x1, y1, x2, y2, confidence, class_idx])
                else:
                    page_elements.append([class_idx, x1, y1, x2, y2])
            page_tensor = torch.tensor(page_elements)
            pages_list.append(page_tensor)

        return pages_list

    @staticmethod
    def _get_top_k_idx_per_cls(
        preds_scores: torch.Tensor, preds_cls: torch.Tensor, top_k: int
    ) -> torch.Tensor:
        # From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Get the indexes of all the top k predictions for every class

        Args:
            preds_scores:   The confidence scores, vector of shape (n_pred)
            preds_cls:      The predicted class, vector of shape (n_pred)
            top_k:          Number of predictions to keep per class, ordered by confidence score

        Returns:
            top_k_idx:     Indexes of the top k predictions. length <= (k * n_unique_class)
        """
        n_unique_cls = torch.max(preds_cls)
        mask = preds_cls.view(-1, 1) == torch.arange(
            n_unique_cls + 1, device=preds_scores.device
        ).view(1, -1)
        preds_scores_per_cls = preds_scores.view(-1, 1) * mask

        sorted_scores_per_cls, sorting_idx = preds_scores_per_cls.sort(0, descending=True)
        idx_with_satisfying_scores = sorted_scores_per_cls[:top_k, :].nonzero(as_tuple=False)
        top_k_idx = sorting_idx[idx_with_satisfying_scores.split(1, dim=1)]
        return top_k_idx.view(-1)

    @staticmethod
    def _change_bbox_bounds_for_image_size(
        boxes: np.ndarray, img_shape: tuple[int, int]
    ) -> np.ndarray:
        # From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Clips bboxes to image boundaries.

        Args:
            bboxes:         Input bounding boxes in XYXY format of [..., 4] shape
            img_shape:      Image shape (height, width).
        Returns:
            clipped_boxes:  Clipped bboxes in XYXY format of [..., 4] shape
        """
        boxes[..., [0, 2]] = boxes[..., [0, 2]].clip(min=0, max=img_shape[1])
        boxes[..., [1, 3]] = boxes[..., [1, 3]].clip(min=0, max=img_shape[0])
        return boxes

    @staticmethod
    def _box_iou(box1: torch.Tensor, box2: torch.Tensor) -> torch.Tensor:
        # From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Return intersection-over-union (Jaccard index) of boxes.
        Both sets of boxes are expected to be in (x1, y1, x2, y2) format.

        Args:
            box1: Tensor of shape [N, 4]
            box2: Tensor of shape [M, 4]

        Returns:
            iou:    Tensor of shape [N, M]: the NxM matrix containing the pairwise IoU values
                    for every element in boxes1 and boxes2
        """

        def box_area(box):
            # box = 4xn
            return (box[2] - box[0]) * (box[3] - box[1])

        area1 = box_area(box1.T)
        area2 = box_area(box2.T)

        # inter(N,M) = (rb(N,M,2) - lt(N,M,2)).clamp(0).prod(2)
        inter = (
            (torch.min(box1[:, None, 2:], box2[:, 2:]) - torch.max(box1[:, None, :2], box2[:, :2]))
            .clamp(0)
            .prod(2)
        )
        return inter / (area1[:, None] + area2 - inter)  # iou = inter / (area1 + area2 - inter)

    def _compute_targets(
        self,
        preds_box_xyxy: torch.Tensor,
        preds_cls: torch.Tensor,
        targets_box_xyxy: torch.Tensor,
        targets_cls: torch.Tensor,
        preds_matched: torch.Tensor,
        targets_matched: torch.Tensor,
        preds_idx_to_use: torch.Tensor,
        iou_thresholds: torch.Tensor,
    ) -> torch.Tensor:
        # From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Computes the matching targets based on IoU for regular scenarios.

        Args:
            preds_box_xyxy: (torch.Tensor) Predicted bounding boxes in XYXY format.
            preds_cls: (torch.Tensor) Predicted classes.
            targets_box_xyxy: (torch.Tensor) Target bounding boxes in XYXY format.
            targets_cls: (torch.Tensor) Target classes.
            preds_matched: (torch.Tensor) Tensor indicating which predictions are matched.
            targets_matched: (torch.Tensor) Tensor indicating which targets are matched.
            preds_idx_to_use: (torch.Tensor) Indices of predictions to use.

        Returns:
            targets: Computed matching targets.
        """
        # shape = (n_preds x n_targets)
        iou = self._box_iou(preds_box_xyxy[preds_idx_to_use], targets_box_xyxy)

        # Fill IoU values at index (i, j) with 0 when the prediction (i) and target(j)
        # are of different class
        # Filling with 0 is equivalent to ignore these values
        # since with want IoU > iou_threshold > 0
        cls_mismatch = preds_cls[preds_idx_to_use].view(-1, 1) != targets_cls.view(1, -1)
        iou[cls_mismatch] = 0

        # The matching priority is first detection confidence and then IoU value.
        # The detection is already sorted by confidence in NMS,
        # so here for each prediction we order the targets by iou.
        sorted_iou, target_sorted = iou.sort(descending=True, stable=True)

        # Only iterate over IoU values higher than min threshold to speed up the process
        for pred_selected_i, target_sorted_i in (sorted_iou > iou_thresholds[0]).nonzero(
            as_tuple=False
        ):
            # pred_selected_i and target_sorted_i are relative to filters/sorting,
            # so we extract their absolute indexes
            pred_i = preds_idx_to_use[pred_selected_i]
            target_i = target_sorted[pred_selected_i, target_sorted_i]

            # Vector[j], True when IoU(pred_i, target_i) is above the (j)th threshold
            is_iou_above_threshold = sorted_iou[pred_selected_i, target_sorted_i] > iou_thresholds

            # Vector[j], True when both pred_i and target_i are not matched yet
            # for the (j)th threshold
            are_candidates_free = torch.logical_and(
                ~preds_matched[pred_i, :], ~targets_matched[target_i, :]
            )

            # Vector[j], True when (pred_i, target_i) can be matched for the (j)th threshold
            are_candidates_good = torch.logical_and(is_iou_above_threshold, are_candidates_free)

            # For every threshold (j) where target_i and pred_i can be matched together
            # ( are_candidates_good[j]==True )
            # fill the matching placeholders with True
            targets_matched[target_i, are_candidates_good] = True
            preds_matched[pred_i, are_candidates_good] = True

            # When all the targets are matched with a prediction for every IoU Threshold, stop.
            if targets_matched.all():
                break

        return preds_matched

    def _compute_page_detection_matching(
        self,
        preds: torch.Tensor,
        targets: torch.Tensor,
        height: int,
        width: int,
        top_k: int = 100,
        return_on_cpu: bool = True,
    ) -> tuple:
        # Adapted from: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Match predictions (NMS output) and the targets (ground truth) with respect to metric
        and confidence score for a given image.

        Args:
            preds:          Tensor of shape (num_img_predictions, 6)
                            format: (x1, y1, x2, y2, confidence, class_label)
                            where x1,y1,x2,y2 are according to image size
            targets:        targets for this image of shape (num_img_targets, 5)
                            format:     (label, x1, y1, x2, y2)
                            where x1,y1,x2,y2 are according to image size
            height:         dimensions of the image
            width:          dimensions of the image
            top_k:          Number of predictions to keep per class, ordered by confidence score
            return_on_cpu:  If True, the output will be returned on "CPU", otherwise it will be
                            returned on "device"

        Returns:
            preds_matched:      Tensor of shape (num_img_predictions, n_thresholds)
                                True when prediction (i) is matched with a target with respect to
                                the (j)th threshold
            preds_to_ignore:    Tensor of shape (num_img_predictions, n_thresholds)
                                True when prediction (i) is matched with a crowd target with
                                respect to the (j)th threshold
            preds_scores:       Tensor of shape (num_img_predictions),
                                confidence score for every prediction
            preds_cls:          Tensor of shape (num_img_predictions),
                                predicted class for every prediction
            targets_cls:        Tensor of shape (num_img_targets),
                                ground truth class for every target
        """
        thresholds = self.iou_thresholds.to(device=self.device)
        num_thresholds = len(thresholds)

        if preds is None or len(preds) == 0:
            preds_matched = torch.zeros((0, num_thresholds), dtype=torch.bool, device=self.device)
            preds_to_ignore = torch.zeros((0, num_thresholds), dtype=torch.bool, device=self.device)
            preds_scores = torch.tensor([], dtype=torch.float32, device=self.device)
            preds_cls = torch.tensor([], dtype=torch.float32, device=self.device)
            targets_cls = targets[:, 0].to(device=self.device)
            return preds_matched, preds_to_ignore, preds_scores, preds_cls, targets_cls

        preds_matched = torch.zeros(
            len(preds), num_thresholds, dtype=torch.bool, device=self.device
        )
        targets_matched = torch.zeros(
            len(targets), num_thresholds, dtype=torch.bool, device=self.device
        )
        preds_to_ignore = torch.zeros(
            len(preds), num_thresholds, dtype=torch.bool, device=self.device
        )

        preds_cls, preds_box, preds_scores = preds[:, -1], preds[:, 0:4], preds[:, 4]
        targets_cls, targets_box = targets[:, 0], targets[:, 1:5]

        # Ignore all but the predictions that were top_k for their class
        preds_idx_to_use = self._get_top_k_idx_per_cls(preds_scores, preds_cls, top_k)
        preds_to_ignore[:, :] = True
        preds_to_ignore[preds_idx_to_use] = False

        if len(targets) > 0:  # or len(crowd_targets) > 0:
            self._change_bbox_bounds_for_image_size(preds, (height, width))

            preds_matched = self._compute_targets(
                preds_box,
                preds_cls,
                targets_box,
                targets_cls,
                preds_matched,
                targets_matched,
                preds_idx_to_use,
                thresholds,
            )

        return preds_matched, preds_to_ignore, preds_scores, preds_cls, targets_cls

    def _compute_detection_metrics(
        self,
        preds_matched: torch.Tensor,
        preds_to_ignore: torch.Tensor,
        preds_scores: torch.Tensor,
        preds_cls: torch.Tensor,
        targets_cls: torch.Tensor,
    ) -> tuple:
        # Adapted from: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Compute the list of precision, recall, MaP and f1 for every class.

        Args:
            preds_matched:      Tensor of shape (num_predictions, n_iou_thresholds)
                                True when prediction (i) is matched with a target with respect
                                to the (j)th IoU threshold
            preds_to_ignore     Tensor of shape (num_predictions, n_iou_thresholds)
                                True when prediction (i) is matched with a crowd target with
                                respect to the (j)th IoU threshold
            preds_scores:       Tensor of shape (num_predictions),
                                confidence score for every prediction
            preds_cls:          Tensor of shape (num_predictions),
                                predicted class for every prediction
            targets_cls:        Tensor of shape (num_targets),
                                ground truth class for every target box to be detected

        Returns:
            ap, precision, recall, f1:  Tensors of shape (n_class, nb_iou_thrs)
            unique_classes:             Vector with all unique target classes
        """

        preds_matched, preds_to_ignore = preds_matched.to(self.device), preds_to_ignore.to(
            self.device
        )
        preds_scores, preds_cls, targets_cls = (
            preds_scores.to(self.device),
            preds_cls.to(self.device),
            targets_cls.to(self.device),
        )

        recall_thresholds = self.recall_thresholds.to(self.device)
        score_threshold = self.score_threshold

        unique_classes = torch.unique(targets_cls).long()

        n_class, nb_iou_thrs = len(unique_classes), preds_matched.shape[-1]

        ap = torch.zeros((n_class, nb_iou_thrs), device=self.device)
        precision = torch.zeros((n_class, nb_iou_thrs), device=self.device)
        recall = torch.zeros((n_class, nb_iou_thrs), device=self.device)

        for cls_i, class_value in enumerate(unique_classes):
            cls_preds_idx, cls_targets_idx = (preds_cls == class_value), (
                targets_cls == class_value
            )
            (
                cls_ap,
                cls_precision,
                cls_recall,
            ) = self._compute_detection_metrics_per_cls(
                preds_matched=preds_matched[cls_preds_idx],
                preds_to_ignore=preds_to_ignore[cls_preds_idx],
                preds_scores=preds_scores[cls_preds_idx],
                n_targets=cls_targets_idx.sum(),
                recall_thresholds=recall_thresholds,
                score_threshold=score_threshold,
            )
            ap[cls_i, :] = cls_ap
            precision[cls_i, :] = cls_precision
            recall[cls_i, :] = cls_recall

        f1 = 2 * precision * recall / (precision + recall + 1e-16)
        return ap, precision, recall, f1, unique_classes

    def _compute_detection_metrics_per_cls(
        self,
        preds_matched: torch.Tensor,
        preds_to_ignore: torch.Tensor,
        preds_scores: torch.Tensor,
        n_targets: int,
        recall_thresholds: torch.Tensor,
        score_threshold: float,
    ):
        # Adapted from: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py  # noqa E501
        """
        Compute the list of precision, recall and MaP of a given class for every recall threshold.

        Args:
            preds_matched:      Tensor of shape (num_predictions, n_thresholds)
                                True when prediction (i) is matched with a target
                                with respect to the(j)th threshold
            preds_to_ignore     Tensor of shape (num_predictions, n_thresholds)
                                True when prediction (i) is matched with a crowd target
                                with respect to the (j)th threshold
            preds_scores:       Tensor of shape (num_predictions),
                                confidence score for every prediction
            n_targets:          Number of target boxes of this class
            recall_thresholds:  Tensor of shape (max_n_rec_thresh)
                                list of recall thresholds used to compute MaP
            score_threshold:    Minimum confidence score to consider a prediction
                                for the computation of precision and recall (not MaP)

        Returns:
            ap, precision, recall:     Tensors of shape (nb_thrs)
        """

        nb_iou_thrs = preds_matched.shape[-1]

        tps = preds_matched
        fps = torch.logical_and(
            torch.logical_not(preds_matched), torch.logical_not(preds_to_ignore)
        )

        if len(tps) == 0:
            return (
                torch.zeros(nb_iou_thrs, device=self.device),
                torch.zeros(nb_iou_thrs, device=self.device),
                torch.zeros(nb_iou_thrs, device=self.device),
            )

        # Sort by decreasing score
        dtype = (
            torch.uint8
            if preds_scores.is_cuda and preds_scores.dtype is torch.bool
            else preds_scores.dtype
        )
        sort_ind = torch.argsort(preds_scores.to(dtype), descending=True)
        tps = tps[sort_ind, :]
        fps = fps[sort_ind, :]
        preds_scores = preds_scores[sort_ind].contiguous()

        # Rolling sum over the predictions
        rolling_tps = torch.cumsum(tps, axis=0, dtype=torch.float)
        rolling_fps = torch.cumsum(fps, axis=0, dtype=torch.float)

        rolling_recalls = rolling_tps / n_targets
        rolling_precisions = rolling_tps / (
            rolling_tps + rolling_fps + torch.finfo(torch.float64).eps
        )

        # Reversed cummax to only have decreasing values
        rolling_precisions = rolling_precisions.flip(0).cummax(0).values.flip(0)

        # ==================
        # RECALL & PRECISION

        # We want the rolling precision/recall at index i so that:
        # preds_scores[i-1] >= score_threshold > preds_scores[i]
        # Note: torch.searchsorted works on increasing sequence and preds_scores is decreasing,
        # so we work with "-"
        # Note2: right=True due to negation
        lowest_score_above_threshold = torch.searchsorted(
            -preds_scores, -score_threshold, right=True
        )

        if (
            lowest_score_above_threshold == 0
        ):  # Here score_threshold > preds_scores[0], so no pred is above the threshold
            recall = torch.zeros(nb_iou_thrs, device=self.device)
            precision = torch.zeros(
                nb_iou_thrs, device=self.device
            )  # the precision is not really defined when no pred but we need to give it a value
        else:
            recall = rolling_recalls[lowest_score_above_threshold - 1]
            precision = rolling_precisions[lowest_score_above_threshold - 1]

        # ==================
        # AVERAGE PRECISION

        # shape = (nb_iou_thrs, n_recall_thresholds)
        recall_thresholds = recall_thresholds.view(1, -1).repeat(nb_iou_thrs, 1)

        # We want the index i so that:
        # rolling_recalls[i-1] < recall_thresholds[k] <= rolling_recalls[i]
        # Note:  when recall_thresholds[k] > max(rolling_recalls), i = len(rolling_recalls)
        # Note2: we work with transpose (.T) to apply torch.searchsorted on first dim
        # instead of the last one
        recall_threshold_idx = torch.searchsorted(
            rolling_recalls.T.contiguous(), recall_thresholds, right=False
        ).T

        # When recall_thresholds[k] > max(rolling_recalls),
        # rolling_precisions[i] is not defined, and we want precision = 0
        rolling_precisions = torch.cat(
            (rolling_precisions, torch.zeros(1, nb_iou_thrs, device=self.device)), dim=0
        )

        # shape = (n_recall_thresholds, nb_iou_thrs)
        sampled_precision_points = torch.gather(
            input=rolling_precisions, index=recall_threshold_idx, dim=0
        )

        # Average over the recall_thresholds
        ap = sampled_precision_points.mean(0)

        return ap, precision, recall

    def get_metrics(self) -> ObjectDetectionEvaluation:
        """Get per document OD metrics.

        Returns:
            output_dict: dict with OD metrics
        """
        document_matchings = []
        for preds, targets, height, width in zip(
            self.document_preds, self.document_targets, self.pages_height, self.pages_width
        ):
            # iterate over each page
            page_matching_tensors = self._compute_page_detection_matching(
                preds=preds,
                targets=targets,
                height=height,
                width=width,
            )
            document_matchings.append(page_matching_tensors)

        # compute metrics for all detections and targets
        mean_ap, mean_precision, mean_recall, mean_f1 = (
            -1.0,
            -1.0,
            -1.0,
            -1.0,
        )
        mean_ap_per_class = np.zeros(self.num_cls)

        mean_precision_per_class = np.zeros(self.num_cls)
        mean_recall_per_class = np.zeros(self.num_cls)
        mean_f1_per_class = np.zeros(self.num_cls)

        if len(document_matchings):
            matching_info_tensors = [torch.cat(x, 0) for x in list(zip(*document_matchings))]

            # shape (n_class, nb_iou_thresh)
            (
                ap_per_present_classes,
                precision_per_present_classes,
                recall_per_present_classes,
                f1_per_present_classes,
                present_classes,
            ) = self._compute_detection_metrics(
                *matching_info_tensors,
            )

            # Precision, recall and f1 are computed for IoU threshold range, averaged over classes
            # results before version 3.0.4 (Dec 11 2022) were computed only for smallest value
            # (i.e IoU 0.5 if metric is @0.5:0.95)
            mean_precision, mean_recall, mean_f1 = (
                precision_per_present_classes.mean(),
                recall_per_present_classes.mean(),
                f1_per_present_classes.mean(),
            )

            # MaP is averaged over IoU thresholds and over classes
            mean_ap = ap_per_present_classes.mean()

            # Fill array of per-class AP scores with values for classes that were present in the
            # dataset
            ap_per_class = ap_per_present_classes.mean(1)
            precision_per_class = precision_per_present_classes.mean(1)
            recall_per_class = recall_per_present_classes.mean(1)
            f1_per_class = f1_per_present_classes.mean(1)
            for i, class_index in enumerate(present_classes):
                mean_ap_per_class[class_index] = float(ap_per_class[i])

                mean_precision_per_class[class_index] = float(precision_per_class[i])
                mean_recall_per_class[class_index] = float(recall_per_class[i])
                mean_f1_per_class[class_index] = float(f1_per_class[i])

        od_evaluation = ObjectDetectionEvaluation(
            f1_score=float(mean_f1),
            precision=float(mean_precision),
            recall=float(mean_recall),
            m_ap=float(mean_ap),
        )

        return od_evaluation


if __name__ == "__main__":
    from dataclasses import asdict

    # Example usage
    prediction_file_paths = [Path("pths/to/predictions.json"), Path("pths/to/predictions2.json")]
    ground_truth_file_paths = [
        Path("pths/to/ground_truth.json"),
        Path("pths/to/ground_truth2.json"),
    ]

    for prediction_file_path, ground_truth_file_path in zip(
        prediction_file_paths, ground_truth_file_paths
    ):
        eval_processor = ObjectDetectionEvalProcessor.from_json_files(
            prediction_file_path, ground_truth_file_path
        )

        metrics: ObjectDetectionEvaluation = eval_processor.get_metrics()
        print(f"Metrics for {ground_truth_file_path.name}:\n{asdict(metrics)}")
