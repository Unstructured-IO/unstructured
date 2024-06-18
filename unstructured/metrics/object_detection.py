"""
TODO: Implement object detection metrics
"""

import numpy as np
import torch


class ObjectDetectionEvalProcessor:

    thresholds = torch.tensor(
        [0.5000, 0.5500, 0.6000, 0.6500, 0.7000, 0.7500, 0.8000, 0.8500, 0.9000, 0.9500]
    )
    score_threshold = 0.1
    recall_thresholds = torch.tensor(
        [
            0.0000,
            0.0100,
            0.0200,
            0.0300,
            0.0400,
            0.0500,
            0.0600,
            0.0700,
            0.0800,
            0.0900,
            0.1000,
            0.1100,
            0.1200,
            0.1300,
            0.1400,
            0.1500,
            0.1600,
            0.1700,
            0.1800,
            0.1900,
            0.2000,
            0.2100,
            0.2200,
            0.2300,
            0.2400,
            0.2500,
            0.2600,
            0.2700,
            0.2800,
            0.2900,
            0.3000,
            0.3100,
            0.3200,
            0.3300,
            0.3400,
            0.3500,
            0.3600,
            0.3700,
            0.3800,
            0.3900,
            0.4000,
            0.4100,
            0.4200,
            0.4300,
            0.4400,
            0.4500,
            0.4600,
            0.4700,
            0.4800,
            0.4900,
            0.5000,
            0.5100,
            0.5200,
            0.5300,
            0.5400,
            0.5500,
            0.5600,
            0.5700,
            0.5800,
            0.5900,
            0.6000,
            0.6100,
            0.6200,
            0.6300,
            0.6400,
            0.6500,
            0.6600,
            0.6700,
            0.6800,
            0.6900,
            0.7000,
            0.7100,
            0.7200,
            0.7300,
            0.7400,
            0.7500,
            0.7600,
            0.7700,
            0.7800,
            0.7900,
            0.8000,
            0.8100,
            0.8200,
            0.8300,
            0.8400,
            0.8500,
            0.8600,
            0.8700,
            0.8800,
            0.8900,
            0.9000,
            0.9100,
            0.9200,
            0.9300,
            0.9400,
            0.9500,
            0.9600,
            0.9700,
            0.9800,
            0.9900,
            1.0000,
        ]
    )

    def __init__(  # from_json_file
        self,
        prediction_file_path: str,
        ground_truth_file_path: str,
        device: str = "cuda:0",
    ):
        """Initializes the ObjectDetection prediction and ground truth,
        and converts the data to the required format.

        Args:
            prediction_file_path (_type_): _description_
            ground_truth_file_path (_type_): _description_

        At the and we need to have the following format:
        self.document_preds:            list (of length pages of document) of Tensors of shape (num_predictions, 6)
                                        format:     (x1, y1, x2, y2, confidence, class_label) where x1,y1,x2,y2 are according to image size
        self.document_targets:          list (of length pages of document) of Tensors of shape (num_targets, 6)
                                        format:     (label, x, y, w, h,) where x,y,w,h are according to image size
        """
        # raise NotImplementedError
        self.device = device

        # mock it for now:
        self.img_height = [640, 640]
        self.img_width = [640, 640]
        self.document_preds = [
            torch.tensor(
                [
                    [2.4856e02, 6.6607e01, 4.2841e02, 1.7063e02, 9.5218e-01, 0.0000e00],
                    [5.8978e01, 3.5843e02, 2.4253e02, 4.2172e02, 9.4439e-01, 0.0000e00],
                    [6.0912e01, 2.2883e02, 2.4813e02, 3.5884e02, 9.4188e-01, 0.0000e00],
                    [6.1193e01, 4.2226e02, 2.4496e02, 5.3455e02, 9.3515e-01, 0.0000e00],
                    [2.5118e02, 2.5900e02, 4.3003e02, 3.0006e02, 9.3203e-01, 0.0000e00],
                    [6.1027e01, 1.3312e02, 2.3963e02, 1.9875e02, 9.3171e-01, 0.0000e00],
                    [2.4368e02, 1.7002e02, 4.2906e02, 2.1887e02, 9.3026e-01, 0.0000e00],
                    [6.1644e01, 5.3534e02, 2.4245e02, 5.7673e02, 9.2585e-01, 0.0000e00],
                    [2.4585e02, 5.4949e02, 4.2816e02, 5.8169e02, 9.2502e-01, 0.0000e00],
                    [2.4628e02, 4.8424e02, 4.2938e02, 5.2543e02, 9.2340e-01, 0.0000e00],
                    [2.4775e02, 2.9970e02, 4.2738e02, 3.6746e02, 9.2260e-01, 0.0000e00],
                    [6.1067e01, 5.7634e02, 2.4246e02, 5.9378e02, 9.0399e-01, 0.0000e00],
                    [2.4646e02, 5.2485e02, 4.2861e02, 5.4980e02, 9.0336e-01, 0.0000e00],
                    [2.4919e02, 3.6586e02, 4.2834e02, 4.3672e02, 9.0137e-01, 0.0000e00],
                    [2.5594e02, 4.3513e02, 4.2861e02, 4.8442e02, 8.9275e-01, 0.0000e00],
                    [9.1435e01, 2.0499e02, 2.0733e02, 2.2173e02, 8.9103e-01, 9.0000e00],
                    [2.5060e02, 2.4280e02, 4.2787e02, 2.5886e02, 8.8879e-01, 0.0000e00],
                    [2.4397e02, 2.2663e02, 4.3023e02, 2.4286e02, 8.8307e-01, 0.0000e00],
                    [6.3667e01, 6.6061e01, 2.4091e02, 1.3194e02, 8.2293e-01, 0.0000e00],
                    [2.0605e02, 4.2774e01, 2.8249e02, 5.5234e01, 7.0306e-01, 4.0000e00],
                    [6.2395e01, 1.1820e02, 2.4050e02, 1.3387e02, 5.8918e-01, 0.0000e00],
                    [2.5028e02, 2.1909e02, 3.4056e02, 2.2590e02, 4.9535e-01, 0.0000e00],
                    [6.2513e01, 5.2795e02, 1.1843e02, 5.3571e02, 4.8663e-01, 0.0000e00],
                ],
                device=self.device,
            ),
            torch.tensor(
                [
                    [4.2371e02, 1.2068e02, 6.1859e02, 2.2649e02, 9.5651e-01, 0.0000e00],
                    [1.9362e01, 5.6709e01, 2.1371e02, 1.6207e02, 9.5439e-01, 0.0000e00],
                    [2.1843e02, 3.4317e02, 4.1325e02, 3.9608e02, 9.4542e-01, 0.0000e00],
                    [1.7543e01, 3.3258e02, 2.1111e02, 4.0717e02, 9.4286e-01, 0.0000e00],
                    [2.1945e02, 2.6870e02, 4.2068e02, 3.3246e02, 9.4237e-01, 0.0000e00],
                    [4.2269e02, 5.6971e01, 6.1517e02, 1.0931e02, 9.4223e-01, 0.0000e00],
                    [4.1963e02, 2.3676e02, 6.1160e02, 3.0146e02, 9.3920e-01, 0.0000e00],
                    [1.8775e01, 2.7930e02, 2.0394e02, 3.2200e02, 9.3886e-01, 0.0000e00],
                    [2.2226e02, 1.9484e02, 4.1299e02, 2.5776e02, 9.3568e-01, 0.0000e00],
                    [2.2404e01, 2.0651e02, 2.1787e02, 2.6854e02, 9.2975e-01, 0.0000e00],
                    [1.9024e01, 1.7276e02, 2.1162e02, 2.0438e02, 9.1410e-01, 9.0000e00],
                    [2.2031e02, 1.7236e02, 4.1636e02, 1.9349e02, 9.1259e-01, 9.0000e00],
                    [3.5116e02, 1.6785e01, 6.1536e02, 2.5246e01, 8.7047e-01, 8.0000e00],
                    [5.3377e02, 4.2658e02, 6.0098e02, 4.3356e02, 8.3789e-01, 1.1000e01],
                    [1.8970e01, 1.3712e01, 8.2764e01, 3.0092e01, 8.1459e-01, 4.0000e00],
                    [4.8667e02, 4.2667e02, 5.2461e02, 4.3325e02, 8.1318e-01, 1.1000e01],
                    [6.1207e02, 4.2653e02, 6.1956e02, 4.3316e02, 7.4768e-01, 1.0000e00],
                    [2.2432e02, 1.0925e02, 3.1043e02, 1.2507e02, 7.2642e-01, 6.0000e00],
                    [3.2015e02, 5.8529e01, 3.8141e02, 7.4261e01, 6.8378e-01, 6.0000e00],
                    [2.2392e02, 1.4804e02, 2.5732e02, 1.5699e02, 6.4333e-01, 1.2000e01],
                    [2.2401e02, 1.3347e02, 3.1337e02, 1.4384e02, 6.1078e-01, 1.2000e01],
                    [5.2745e02, 4.2671e02, 5.3047e02, 4.3361e02, 6.0299e-01, 7.0000e00],
                    [3.2029e02, 1.2998e02, 4.0498e02, 1.5287e02, 5.5048e-01, 0.0000e00],
                    [3.2019e02, 1.0554e02, 4.1018e02, 1.2785e02, 5.3782e-01, 0.0000e00],
                    [6.0564e02, 4.2712e02, 6.0828e02, 4.3374e02, 2.5115e-01, 7.0000e00],
                ],
                device=self.device,
            ),
        ]
        self.document_targets = [
            torch.tensor(
                [
                    [0.0000, 244.2072, 49.3847, 72.2981, 8.4452],
                    [0.0000, 150.3265, 60.6566, 4.3129, 7.5245],
                    [0.0000, 150.4814, 74.9382, 174.3593, 13.5913],
                    [0.0000, 150.4349, 92.7185, 174.8247, 15.3916],
                    [0.0000, 150.5280, 109.4749, 174.0800, 15.4531],
                    [0.0000, 150.7840, 125.5796, 173.8473, 14.7084],
                    [0.0000, 150.4037, 165.4537, 174.7009, 62.0609],
                    [9.0000, 150.7095, 213.0716, 112.8969, 13.5643],
                    [0.0000, 150.5434, 253.6727, 175.1664, 47.2902],
                    [0.0000, 150.2022, 298.3098, 175.2902, 38.6327],
                    [0.0000, 150.2799, 338.8197, 174.5762, 39.5944],
                    [0.0000, 150.6057, 390.9586, 174.1107, 62.6036],
                    [0.0000, 150.8385, 479.5424, 174.3900, 112.3300],
                    [0.0000, 150.7142, 556.4044, 174.3593, 39.8429],
                    [0.0000, 150.5359, 584.8902, 173.2264, 15.1738],
                    [0.0000, 338.9440, 60.6953, 4.8407, 6.9818],
                    [0.0000, 339.1767, 118.9548, 174.2662, 102.2762],
                    [0.0000, 339.2386, 193.7999, 174.2355, 45.7700],
                    [0.0000, 297.1462, 222.0218, 75.9622, 5.9578],
                    [0.0000, 339.2698, 234.6203, 173.9869, 15.1431],
                    [0.0000, 342.7607, 250.9265, 167.0051, 15.5462],
                    [0.0000, 342.9702, 279.3193, 167.5171, 39.5637],
                    [0.0000, 343.1331, 331.4734, 167.7498, 63.5345],
                    [0.0000, 342.5433, 400.2756, 167.8736, 71.3383],
                    [0.0000, 343.1331, 460.0087, 168.4946, 46.0800],
                    [0.0000, 339.2852, 505.0647, 174.7009, 39.4389],
                    [0.0000, 339.2233, 537.1811, 174.0800, 23.5520],
                    [0.0000, 339.2931, 565.4109, 174.3127, 30.9527],
                    [7.0000, 244.9278, 547.1832, 5.4756, 4.0728],
                    [7.0000, 244.8156, 506.8963, 5.2401, 4.0355],
                    [7.0000, 244.9022, 466.5651, 5.4393, 3.9229],
                    [7.0000, 244.6429, 426.2372, 5.3993, 3.9619],
                    [7.0000, 244.7360, 385.8153, 5.7865, 4.0029],
                    [7.0000, 244.6946, 345.5069, 5.3164, 4.0029],
                    [7.0000, 244.8291, 305.1469, 5.3993, 3.8996],
                    [7.0000, 244.7825, 264.9395, 5.3062, 3.9042],
                    [7.0000, 244.8044, 224.6284, 5.4486, 3.9545],
                    [7.0000, 244.8891, 184.2981, 4.9068, 3.9536],
                    [7.0000, 244.9687, 143.9348, 5.1200, 3.8772],
                    [7.0000, 244.5964, 103.6265, 2.3273, 3.8772],
                    [7.0000, 317.3935, 588.3346, 2.6996, 3.1651],
                    [7.0000, 328.1454, 588.3346, 2.7927, 3.1651],
                    [7.0000, 339.2698, 588.3378, 2.6996, 2.9724],
                    [7.0000, 350.1149, 588.2880, 2.7927, 3.0720],
                    [7.0000, 361.0065, 588.3057, 2.6065, 3.0366],
                ],
                device=self.device,
            ),
            torch.tensor(
                [
                    [4.0000, 50.5359, 22.0753, 61.6648, 15.6899],
                    [8.0000, 482.7366, 20.7982, 275.1197, 5.8381],
                    [0.0000, 117.3090, 109.4641, 195.2109, 105.8153],
                    [6.0000, 261.9585, 66.1455, 73.3409, 13.1357],
                    [6.0000, 350.8324, 66.4082, 59.4755, 13.8655],
                    [6.0000, 238.0844, 81.0034, 25.9065, 7.2976],
                    [6.0000, 267.6397, 95.2337, 85.7469, 15.3250],
                    [6.0000, 267.2748, 116.9441, 85.0171, 15.6898],
                    [6.0000, 267.6397, 139.3843, 86.4766, 8.7571],
                    [6.0000, 239.9088, 152.7024, 30.2851, 6.9327],
                    [6.0000, 338.9738, 81.0034, 35.7583, 8.0274],
                    [6.0000, 345.5416, 99.1124, 48.8940, 7.6625],
                    [6.0000, 351.9270, 109.8290, 62.3945, 6.5678],
                    [6.0000, 364.5154, 120.5929, 87.5713, 14.2303],
                    [6.0000, 362.1437, 138.8369, 82.8278, 14.9601],
                    [6.0000, 341.7104, 152.7024, 41.9612, 7.6625],
                    [5.0000, 318.6773, 107.7400, 191.6534, 99.4481],
                    [9.0000, 116.9259, 189.0080, 194.7950, 32.1095],
                    [0.0000, 117.4914, 236.9897, 194.8461, 63.1243],
                    [0.0000, 111.2885, 300.8438, 180.9806, 41.2315],
                    [0.0000, 115.8495, 370.5359, 190.1026, 73.3409],
                    [9.0000, 319.0878, 183.5348, 193.7514, 19.7035],
                    [0.0000, 316.7161, 226.5907, 189.0080, 63.4892],
                    [0.0000, 318.1884, 300.8310, 192.0036, 62.4712],
                    [0.0000, 316.7161, 370.1710, 189.7377, 52.9076],
                    [0.0000, 517.1156, 82.3097, 186.4538, 53.2725],
                    [0.0000, 522.1437, 173.6830, 194.8461, 105.0855],
                    [0.0000, 516.4880, 268.9167, 184.2646, 62.0296],
                    [11.0000, 567.0239, 430.7411, 66.4082, 4.7434],
                    [1.0000, 615.3706, 430.5587, 6.9327, 4.3786],
                    [11.0000, 505.1767, 430.7411, 35.3934, 4.7434],
                ],
                device=self.device,
            ),
        ]
        # TODO: Implement parsings after https://unstructured-ai.atlassian.net/browse/ML-88
        # and https://unstructured-ai.atlassian.net/browse/ML-92 are done.

    def _get_top_k_idx_per_cls(
        preds_scores: torch.Tensor, preds_cls: torch.Tensor, top_k: int
    ) -> torch.Tensor:
        """Get the indexes of all the top k predictions for every class
        From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py
        :param preds_scores:   The confidence scores, vector of shape (n_pred)
        :param preds_cls:      The predicted class, vector of shape (n_pred)
        :param top_k:          Number of predictions to keep per class, ordered by confidence score

        :return top_k_idx:     Indexes of the top k predictions. length <= (k * n_unique_class)
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

    def _change_bbox_bounds_for_image_size(
        boxes: np.ndarray, img_shape: tuple[int, int]
    ) -> np.ndarray:
        """
        Clips bboxes to image boundaries.
        From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py

        :param bboxes:     (np.ndarray) Input bounding boxes in XYXY format of [..., 4] shape
        :param img_shape:  Tuple[int,int] of image shape (height, width).
        :return:           (np.ndarray)clipped bboxes in XYXY format of [..., 4] shape
        """
        boxes[..., [0, 2]] = boxes[..., [0, 2]].clip(min=0, max=img_shape[1])
        boxes[..., [1, 3]] = boxes[..., [1, 3]].clip(min=0, max=img_shape[0])
        return boxes

    def _cxcywh2xyxy(bboxes: torch.Tensor | np.array) -> torch.Tensor | np.array:
        """
        Transforms bboxes from centerized xy wh format to xyxy format
        From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py

        :param bboxes: array, shaped (nboxes, 4)
        :return: modified bboxes
        """
        bboxes[:, 1] = bboxes[:, 1] - bboxes[:, 3] * 0.5
        bboxes[:, 0] = bboxes[:, 0] - bboxes[:, 2] * 0.5
        bboxes[:, 3] = bboxes[:, 3] + bboxes[:, 1]
        bboxes[:, 2] = bboxes[:, 2] + bboxes[:, 0]
        return bboxes

    def _box_iou(box1: torch.Tensor, box2: torch.Tensor) -> torch.Tensor:
        # https://github.com/pytorch/vision/blob/master/torchvision/ops/boxes.py
        """
        Return intersection-over-union (Jaccard index) of boxes.
        Both sets of boxes are expected to be in (x1, y1, x2, y2) format.
        :param box1: Tensor of shape [N, 4]
        :param box2: Tensor of shape [M, 4]
        :return:     iou, Tensor of shape [N, M]: the NxM matrix containing the pairwise IoU values for every element in boxes1 and boxes2
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
        """
        Computes the matching targets based on IoU for regular scenarios.
        From: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py

        :param preds_box_xyxy: (torch.Tensor) Predicted bounding boxes in XYXY format.
        :param preds_cls: (torch.Tensor) Predicted classes.
        :param targets_box_xyxy: (torch.Tensor) Target bounding boxes in XYXY format.
        :param targets_cls: (torch.Tensor) Target classes.
        :param preds_matched: (torch.Tensor) Tensor indicating which predictions are matched.
        :param targets_matched: (torch.Tensor) Tensor indicating which targets are matched.
        :param preds_idx_to_use: (torch.Tensor) Indices of predictions to use.
        :return: (torch.Tensor) Computed matching targets.
        """
        # shape = (n_preds x n_targets)
        iou = self._box_iou(preds_box_xyxy[preds_idx_to_use], targets_box_xyxy)

        # Fill IoU values at index (i, j) with 0 when the prediction (i) and target(j) are of different class
        # Filling with 0 is equivalent to ignore these values since with want IoU > iou_threshold > 0
        cls_mismatch = preds_cls[preds_idx_to_use].view(-1, 1) != targets_cls.view(1, -1)
        iou[cls_mismatch] = 0

        # The matching priority is first detection confidence and then IoU value.
        # The detection is already sorted by confidence in NMS, so here for each prediction we order the targets by iou.
        sorted_iou, target_sorted = iou.sort(descending=True, stable=True)

        # Only iterate over IoU values higher than min threshold to speed up the process
        for pred_selected_i, target_sorted_i in (sorted_iou > iou_thresholds[0]).nonzero(
            as_tuple=False
        ):
            # pred_selected_i and target_sorted_i are relative to filters/sorting, so we extract their absolute indexes
            pred_i = preds_idx_to_use[pred_selected_i]
            target_i = target_sorted[pred_selected_i, target_sorted_i]

            # Vector[j], True when IoU(pred_i, target_i) is above the (j)th threshold
            is_iou_above_threshold = sorted_iou[pred_selected_i, target_sorted_i] > iou_thresholds

            # Vector[j], True when both pred_i and target_i are not matched yet for the (j)th threshold
            are_candidates_free = torch.logical_and(
                ~preds_matched[pred_i, :], ~targets_matched[target_i, :]
            )

            # Vector[j], True when (pred_i, target_i) can be matched for the (j)th threshold
            are_candidates_good = torch.logical_and(is_iou_above_threshold, are_candidates_free)

            # For every threshold (j) where target_i and pred_i can be matched together ( are_candidates_good[j]==True )
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
        """
        Match predictions (NMS output) and the targets (ground truth) with respect to metric and confidence score
        for a given image.
        Adapted from: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py

        :param preds:           Tensor of shape (num_img_predictions, 6)
                                format:     (x1, y1, x2, y2, confidence, class_label) where x1,y1,x2,y2 are according to image size
        :param targets:         targets for this image of shape (num_img_targets, 6)
                                format:     (label, cx, cy, w, h) where cx,cy,w,h
        :param height:          dimensions of the image
        :param width:           dimensions of the image
        :param top_k:           Number of predictions to keep per class, ordered by confidence score
        :param return_on_cpu:   If True, the output will be returned on "CPU", otherwise it will be returned on "device"

        :return:
            :preds_matched:     Tensor of shape (num_img_predictions, n_thresholds)
                                    True when prediction (i) is matched with a target with respect to the (j)th threshold
            :preds_to_ignore:   Tensor of shape (num_img_predictions, n_thresholds)
                                    True when prediction (i) is matched with a crowd target with respect to the (j)th threshold
            :preds_scores:      Tensor of shape (num_img_predictions), confidence score for every prediction
            :preds_cls:         Tensor of shape (num_img_predictions), predicted class for every prediction
            :targets_cls:       Tensor of shape (num_img_targets), ground truth class for every target
        """
        thresholds = self.thresholds.to(device=self.device)
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

            targets_box = self._cxcywh2xyxy(targets_box)

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
        """
        Compute the list of precision, recall, MaP and f1 for every recall IoU threshold and for every class.
        Adapted from: https://github.com/Deci-AI/super-gradients/blob/master/src/super_gradients/training/utils/detection_utils.py

        :param preds_matched:      Tensor of shape (num_predictions, n_iou_thresholds)
                                        True when prediction (i) is matched with a target with respect to the (j)th IoU threshold
        :param preds_to_ignore     Tensor of shape (num_predictions, n_iou_thresholds)
                                        True when prediction (i) is matched with a crowd target with respect to the (j)th IoU threshold
        :param preds_scores:       Tensor of shape (num_predictions), confidence score for every prediction
        :param preds_cls:          Tensor of shape (num_predictions), predicted class for every prediction
        :param targets_cls:        Tensor of shape (num_targets), ground truth class for every target box to be detected

        :return:
            :ap, precision, recall, f1: Tensors of shape (n_class, nb_iou_thrs)
            :unique_classes:            Vector with all unique target classes

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

        nb_score_thrs = len(recall_thresholds)
        f1_per_class_per_threshold = torch.zeros((n_class, nb_score_thrs), device=self.device)

        for cls_i, class_value in enumerate(unique_classes):
            cls_preds_idx, cls_targets_idx = (preds_cls == class_value), (
                targets_cls == class_value
            )
            cls_ap, cls_precision, cls_recall, cls_f1_per_threshold = (
                self._compute_detection_metrics_per_cls(
                    preds_matched=preds_matched[cls_preds_idx],
                    preds_to_ignore=preds_to_ignore[cls_preds_idx],
                    preds_scores=preds_scores[cls_preds_idx],
                    n_targets=cls_targets_idx.sum(),
                    recall_thresholds=recall_thresholds,
                    score_threshold=score_threshold,
                )
            )
            ap[cls_i, :] = cls_ap
            precision[cls_i, :] = cls_precision
            recall[cls_i, :] = cls_recall

            f1_per_class_per_threshold[cls_i, :] = cls_f1_per_threshold

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
        """
        Compute the list of precision, recall and MaP of a given class for every recall threshold.

        :param preds_matched:      Tensor of shape (num_predictions, n_thresholds)
                                        True when prediction (i) is matched with a target
                                        with respect to the(j)th threshold
        :param preds_to_ignore     Tensor of shape (num_predictions, n_thresholds)
                                        True when prediction (i) is matched with a crowd target
                                        with respect to the (j)th threshold
        :param preds_scores:       Tensor of shape (num_predictions), confidence score for every prediction
        :param n_targets:          Number of target boxes of this class
        :param recall_thresholds:  Tensor of shape (max_n_rec_thresh) list of recall thresholds used to compute MaP
        :param score_threshold:    Minimum confidence score to consider a prediction for the computation of
                                        precision and recall (not MaP)

        :return:
            :ap, precision, recall:     Tensors of shape (nb_thrs)
            :mean_f1_per_threshold:     Tensor of shape (nb_score_thresholds) if calc_best_score_thresholds is True else None
            :best_score_threshold:      torch.float if calc_best_score_thresholds is True else None
        """

        nb_iou_thrs = preds_matched.shape[-1]
        nb_score_thrs = len(recall_thresholds)

        mean_f1_per_threshold = torch.zeros(nb_score_thrs, device=self.device)
        best_score_threshold = torch.tensor(0.0, dtype=torch.float, device=self.device)

        tps = preds_matched
        fps = torch.logical_and(
            torch.logical_not(preds_matched), torch.logical_not(preds_to_ignore)
        )

        if len(tps) == 0:
            return (
                torch.zeros(nb_iou_thrs, device=self.device),
                torch.zeros(nb_iou_thrs, device=self.device),
                torch.zeros(nb_iou_thrs, device=self.device),
                mean_f1_per_threshold,
                best_score_threshold,
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

        # We want the rolling precision/recall at index i so that: preds_scores[i-1] >= score_threshold > preds_scores[i]
        # Note: torch.searchsorted works on increasing sequence and preds_scores is decreasing, so we work with "-"
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
        # BEST CONFIDENCE SCORE THRESHOLD PER CLASS
        all_score_thresholds = torch.linspace(0, 1, nb_score_thrs, device=self.device)

        # We want the rolling precision/recall at index i so that: preds_scores[i-1] > score_threshold >= preds_scores[i]
        # Note: torch.searchsorted works on increasing sequence and preds_scores is decreasing, so we work with "-"
        lowest_scores_above_thresholds = torch.searchsorted(
            -preds_scores, -all_score_thresholds, right=True
        )

        # When score_threshold > preds_scores[0], then no pred is above the threshold, so we pad with zeros
        rolling_recalls_padded = torch.cat(
            (torch.zeros(1, nb_iou_thrs, device=self.device), rolling_recalls), dim=0
        )
        rolling_precisions_padded = torch.cat(
            (torch.zeros(1, nb_iou_thrs, device=self.device), rolling_precisions), dim=0
        )

        # shape = (n_score_thresholds, nb_iou_thrs)
        recalls_per_threshold = torch.index_select(
            input=rolling_recalls_padded, dim=0, index=lowest_scores_above_thresholds
        )
        precisions_per_threshold = torch.index_select(
            input=rolling_precisions_padded, dim=0, index=lowest_scores_above_thresholds
        )

        # shape (n_score_thresholds, nb_iou_thrs)
        f1_per_threshold = (
            2
            * recalls_per_threshold
            * precisions_per_threshold
            / (recalls_per_threshold + precisions_per_threshold + 1e-16)
        )
        mean_f1_per_threshold = torch.mean(f1_per_threshold, dim=1)  # average over iou thresholds
        best_score_threshold = all_score_thresholds[torch.argmax(mean_f1_per_threshold)]

        # ==================
        # AVERAGE PRECISION

        # shape = (nb_iou_thrs, n_recall_thresholds)
        recall_thresholds = recall_thresholds.view(1, -1).repeat(nb_iou_thrs, 1)

        # We want the index i so that: rolling_recalls[i-1] < recall_thresholds[k] <= rolling_recalls[i]
        # Note:  when recall_thresholds[k] > max(rolling_recalls), i = len(rolling_recalls)
        # Note2: we work with transpose (.T) to apply torch.searchsorted on first dim instead of the last one
        recall_threshold_idx = torch.searchsorted(
            rolling_recalls.T.contiguous(), recall_thresholds, right=False
        ).T

        # When recall_thresholds[k] > max(rolling_recalls), rolling_precisions[i] is not defined, and we want precision = 0
        rolling_precisions = torch.cat(
            (rolling_precisions, torch.zeros(1, nb_iou_thrs, device=self.device)), dim=0
        )

        # shape = (n_recall_thresholds, nb_iou_thrs)
        sampled_precision_points = torch.gather(
            input=rolling_precisions, index=recall_threshold_idx, dim=0
        )

        # Average over the recall_thresholds
        ap = sampled_precision_points.mean(0)

        return ap, precision, recall, mean_f1_per_threshold, best_score_threshold

    def get_metrics(self):
        document_matchings = []
        for preds, targets, height, width in zip(
            self.document_preds, self.document_targets, self.page_height, self.page_width
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
        mean_ap, mean_precision, mean_recall, mean_f1, best_score_threshold = (
            -1.0,
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
            # results before version 3.0.4 (Dec 11 2022) were computed only for smallest value (i.e IoU 0.5 if metric is @0.5:0.95)
            mean_precision, mean_recall, mean_f1 = (
                precision_per_present_classes.mean(),
                recall_per_present_classes.mean(),
                f1_per_present_classes.mean(),
            )

            # MaP is averaged over IoU thresholds and over classes
            mean_ap = ap_per_present_classes.mean()

            # Fill array of per-class AP scores with values for classes that were present in the dataset
            ap_per_class = ap_per_present_classes.mean(1)
            precision_per_class = precision_per_present_classes.mean(1)
            recall_per_class = recall_per_present_classes.mean(1)
            f1_per_class = f1_per_present_classes.mean(1)
            for i, class_index in enumerate(present_classes):
                mean_ap_per_class[class_index] = float(ap_per_class[i])

                mean_precision_per_class[class_index] = float(precision_per_class[i])
                mean_recall_per_class[class_index] = float(recall_per_class[i])
                mean_f1_per_class[class_index] = float(f1_per_class[i])

        return  # TODO what ?
