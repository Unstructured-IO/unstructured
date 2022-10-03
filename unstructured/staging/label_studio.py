from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from unstructured.documents.elements import Text


LABEL_STUDIO_TYPE = List[Dict[str, Dict[str, str]]]


@dataclass
class LabelStudioResult:
    """Class for representing a LabelStudio annotation result.
    ref: https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks"""

    id: str
    type: str  # The type of tag used to annotate the task
    value: Dict[str, Any]  # The values for
    # NOTE(robinson) - See here for a list of object and control tags. Also provides the formats
    # for the value parameter
    # ref: https://labelstud.io/tags/
    from_name: str = "tag"  # Name of the source object tag
    to_name: str = "text"  # Name of the destination control tag

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

    id: str
    lead_time: float  # Time in seconds to label the task
    result: LabelStudioResult  # The result of the annotation
    reviews: List[LabelStudioReview]  # An array consisting of the review results
    completed_by: int  # User ID for the user who completed the task
    was_canceled: bool = False  # Indicates whether or not the annotation was canceled

    def to_dict(self):
        annotation_dict = deepcopy(self.__dict__)
        annotation_dict["result"] = annotation_dict["result"].to_dict()
        if "reviews" in annotation_dict:
            annotation_dict["reviews"] = [r.to_dict() for r in annotation_dict["reviews"]]
        return annotation_dict


def stage_for_label_studio(
    elements: List[Text],
    annotations: Optional[List[Optional[LabelStudioAnnotation]]] = None,
    text_field: str = "text",
    id_field: str = "ref_id",
) -> LABEL_STUDIO_TYPE:
    """Converts the document to the format required for upload to LabelStudio.
    ref: https://labelstud.io/guide/tasks.html#Example-JSON-format"""
    if annotations is not None:
        if len(elements) != len(annotations):
            raise ValueError("The length of elements and annotations must match.")

    label_studio_data: LABEL_STUDIO_TYPE = list()
    for element in elements:
        data: Dict[str, str] = dict()
        data[text_field] = element.text
        if isinstance(element.id, str):
            data[id_field] = element.id
        label_studio_data.append({"data": data})
    return label_studio_data
