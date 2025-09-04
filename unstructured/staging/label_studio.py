from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from unstructured.documents.elements import Element
from unstructured.logger import logger

LABEL_STUDIO_TYPE = List[Dict[str, Dict[str, str]]]

# NOTE(robinson) - ref: https://labelstud.io/tags/labels.html
VALID_LABEL_TYPES = [
    "labels",
    "hypertextlabels",
    "paragraphlabels",
    "rectangle",
    "keypoint",
    "polygon",
    "brush",
    "ellipse",
    "rectanglelabels",
    "keypointlabels",
    "polygonlabels",
    "brushlabels",
    "ellipselabels",
    "timeserieslabels",
    "choices",
    "number",
    "taxonomy",
    "textarea",
    "rating",
    "pairwise",
    "videorectangle",
]


@dataclass
class LabelStudioResult:
    """Class for representing a LabelStudio annotation result.
    ref: https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks"""

    type: str  # The type of tag used to annotate the task
    value: Dict[str, Any]  # The values for
    from_name: str  # Name of the source object tag (i.e. "sentiment" for the sentiment template)
    to_name: str  # Name of the destination control tag
    id: Optional[str] = None
    hidden: bool = False
    read_only: bool = False

    def __post_init__(self):
        if self.type not in VALID_LABEL_TYPES:
            raise ValueError(
                f"{self.type} is not a valid label type. "
                f"Valid label types are: {VALID_LABEL_TYPES}",
            )

    def to_dict(self):
        return self.__dict__


@dataclass
class LabelStudioReview:
    """Class for representing a LablStudio review. Reviews are only available in the
    Enterprise offering.
    ref: https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks"""

    created_by: Dict[str, Union[str, int]]
    accepted: bool
    id: Optional[str] = None

    def to_dict(self):
        return self.__dict__


@dataclass
class LabelStudioAnnotation:
    """Class for representing LabelStudio annotations.
    ref: https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks"""

    result: List[LabelStudioResult]  # The result of the annotation
    id: Optional[str] = None
    lead_time: Optional[float] = None  # Time in seconds to label the task
    completed_by: Optional[int] = None  # User ID for the user who completed the task
    reviews: Optional[List[LabelStudioReview]] = None  # An array of the review results
    was_canceled: bool = False  # Indicates whether or not the annotation was canceled

    def to_dict(self):
        annotation_dict = deepcopy(self.__dict__)
        annotation_dict["result"] = [r.to_dict() for r in annotation_dict["result"]]
        if "reviews" in annotation_dict and annotation_dict["reviews"] is not None:
            annotation_dict["reviews"] = [r.to_dict() for r in annotation_dict["reviews"]]

        # NOTE(robinson) - Removes keys for any fields that defaulted to None
        _annotation_dict = deepcopy(annotation_dict)
        for key, value in annotation_dict.items():
            if value is None:
                _annotation_dict.pop(key)

        return _annotation_dict


@dataclass
class LabelStudioPrediction(LabelStudioAnnotation):
    score: float = 0

    def __post_init__(self):
        if not isinstance(self.score, (int, float)) or (self.score < 0 or self.score > 1):
            raise ValueError(
                f"{self.score} is not a valid score value. "
                f"Score value must be a number between 0 and 1.",
            )


def stage_for_label_studio(
    elements: List[Element],
    annotations: Optional[List[List[LabelStudioAnnotation]]] = None,
    predictions: Optional[List[List[LabelStudioPrediction]]] = None,
    text_field: str = "text",
    id_field: str = "ref_id",
) -> LABEL_STUDIO_TYPE:
    """Converts the document to the format required for upload to LabelStudio.
    ref: https://labelstud.io/guide/tasks.html#Example-JSON-format"""
    # NOTE(alan): The background for this is that we test this function with the package
    # label_studio_sdk, and we're stuck on a version with a high CVE unless we drop to version 1 of
    # numpy. The least bad way forward was to deprecate the function, remove the test, and drop the
    # dependency.
    logger.warning("This function is deprecated, and is unlikely to be maintained in the future.")
    if annotations is not None and len(elements) != len(annotations):
        raise ValueError("The length of elements and annotations must match.")
    if predictions is not None and len(elements) != len(predictions):
        raise ValueError("The length of elements and predictions must match.")

    label_studio_data: LABEL_STUDIO_TYPE = []
    for i, element in enumerate(elements):
        data: Dict[str, str] = {}
        data[text_field] = element.text
        if isinstance(element.id, str):
            data[id_field] = element.id

        labeling_example: Dict[str, Any] = {}
        labeling_example["data"] = data
        if annotations is not None:
            labeling_example["annotations"] = [a.to_dict() for a in annotations[i]]
        if predictions is not None:
            labeling_example["predictions"] = [a.to_dict() for a in predictions[i]]
        label_studio_data.append(labeling_example)

    return label_studio_data
