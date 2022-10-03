from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from unstructured.documents.elements import Text


LABEL_STUDIO_TYPE = List[Dict[str, Dict[str, str]]]


VALID_TYPE = [
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
    id: Optional[str] = None
    # NOTE(robinson) - See here for a list of object and control tags. Also provides the formats
    # for the value parameter
    # ref: https://labelstud.io/tags/
    to_name: str = "text"  # Name of the destination control tag
    hidden: bool = False
    read_only: bool = False

    def to_dict(self):
        return self.__dict__


@dataclass
class LabelStudioReview:
    """Class for representing a LablStudio review. Reviews are only available in the
    Enterprise offering.
    ref: https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks"""

    id: str
    # NOTE(robinson) - created_by is a dictionary containing the user ID, email, first name,
    # and last name of the reviewer
    created_by: Dict[str, Union[str, int]]
    accepted: bool

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

        _annotation_dict = deepcopy(annotation_dict)
        for key, value in annotation_dict.items():
            if value is None:
                _annotation_dict.pop(key)

        return _annotation_dict


def stage_for_label_studio(
    elements: List[Text],
    annotations: Optional[List[LabelStudioAnnotation]] = None,
    text_field: str = "text",
    id_field: str = "ref_id",
) -> LABEL_STUDIO_TYPE:
    """Converts the document to the format required for upload to LabelStudio.
    ref: https://labelstud.io/guide/tasks.html#Example-JSON-format"""
    if annotations is not None:
        if len(elements) != len(annotations):
            raise ValueError("The length of elements and annotations must match.")

    label_studio_data: LABEL_STUDIO_TYPE = list()
    for i, element in enumerate(elements):
        data: Dict[str, str] = dict()
        data[text_field] = element.text
        if isinstance(element.id, str):
            data[id_field] = element.id

        labeling_example: Dict[str, Any] = dict()
        labeling_example["data"] = data
        if annotations is not None:
            annotation: LabelStudioAnnotation = annotations[i]
            labeling_example["annotations"] = [annotation.to_dict()]
        label_studio_data.append(labeling_example)

    return label_studio_data
