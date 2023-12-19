import csv
import io
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    Element,
    ElementMetadata,
    NoID,
)
from unstructured.partition.common import exactly_one
from unstructured.utils import dependency_exists, requires_dependencies

if dependency_exists("pandas"):
    import pandas as pd


def _get_metadata_table_fieldnames():
    metadata_fields = list(ElementMetadata.__annotations__.keys())
    metadata_fields.remove("coordinates")
    metadata_fields.extend(
        [
            "sender",
            "coordinates_points",
            "coordinates_system",
            "coordinates_layout_width",
            "coordinates_layout_height",
        ],
    )
    return metadata_fields


TABLE_FIELDNAMES: List[str] = [
    "type",
    "text",
    "element_id",
] + _get_metadata_table_fieldnames()


def convert_to_text(elements: List[Element]) -> str:
    """Converts a list of elements into clean, concatenated text."""
    return "\n".join([e.text for e in elements if hasattr(e, "text") and e.text])


def elements_to_text(
    elements: List[Element],
    filename: Optional[str] = None,
    encoding: str = "utf-8",
) -> Optional[str]:
    """
    Convert the text from the list of elements into clean, concatenated text.
    Saves to a txt file if filename is specified.
    Otherwise, return the text of the elements as a string.
    """
    element_cct = convert_to_text(elements)
    if filename is not None:
        with open(filename, "w", encoding=encoding) as f:
            f.write(element_cct)
            return None
    else:
        return element_cct


def convert_to_isd(elements: List[Element]) -> List[Dict[str, Any]]:
    """Represents the document elements as an Initial Structured Document (ISD)."""
    isd: List[Dict[str, Any]] = []
    for element in elements:
        section = element.to_dict()
        isd.append(section)
    return isd


def convert_to_dict(elements: List[Element]) -> List[Dict[str, Any]]:
    """Converts a list of elements into a dictionary."""
    return convert_to_isd(elements)


def _fix_metadata_field_precision(elements: List[Element]) -> List[Element]:
    out_elements = []
    for element in elements:
        el = deepcopy(element)
        if el.metadata.coordinates:
            precision = 1 if isinstance(el.metadata.coordinates.system, PixelSpace) else 2
            points = el.metadata.coordinates.points
            rounded_points = []
            for point in points:
                x, y = point
                rounded_point = (round(x, precision), round(y, precision))
                rounded_points.append(rounded_point)
            el.metadata.coordinates.points = tuple(rounded_points)

        if el.metadata.detection_class_prob:
            el.metadata.detection_class_prob = round(el.metadata.detection_class_prob, 5)

        out_elements.append(el)
    return out_elements


def elements_to_json(
    elements: List[Element],
    filename: Optional[str] = None,
    indent: int = 4,
    encoding: str = "utf-8",
) -> Optional[str]:
    """
    Saves a list of elements to a JSON file if filename is specified.
    Otherwise, return the list of elements as a string.
    """

    pre_processed_elements = _fix_metadata_field_precision(elements)
    element_dict = convert_to_dict(pre_processed_elements)
    if filename is not None:
        with open(filename, "w", encoding=encoding) as f:
            json.dump(element_dict, f, indent=indent, sort_keys=True)
            return None
    else:
        return json.dumps(element_dict, indent=indent, sort_keys=True)


def isd_to_elements(isd: List[Dict[str, Any]]) -> List[Element]:
    """Converts an Initial Structured Data (ISD) dictionary to a list of elements."""
    elements: List[Element] = []

    for item in isd:
        element_id: str = item.get("element_id", NoID())
        metadata = ElementMetadata()
        _metadata_dict = item.get("metadata")
        if _metadata_dict is not None:
            metadata = ElementMetadata.from_dict(_metadata_dict)

        if item.get("type") in TYPE_TO_TEXT_ELEMENT_MAP:
            _text_class = TYPE_TO_TEXT_ELEMENT_MAP[item["type"]]
            elements.append(
                _text_class(
                    text=item["text"],
                    element_id=element_id,
                    metadata=metadata,
                ),
            )
        elif item.get("type") == "CheckBox":
            elements.append(
                CheckBox(
                    checked=item["checked"],
                    element_id=element_id,
                    metadata=metadata,
                ),
            )

    return elements


def dict_to_elements(element_dict: List[Dict[str, Any]]) -> List[Element]:
    """Converts a dictionary representation of an element list into List[Element]."""
    return isd_to_elements(element_dict)


def elements_from_json(
    filename: str = "",
    text: str = "",
    encoding: str = "utf-8",
) -> List[Element]:
    """Loads a list of elements from a JSON file or a string."""
    exactly_one(filename=filename, text=text)

    if filename:
        with open(filename, encoding=encoding) as f:
            element_dict = json.load(f)
        return dict_to_elements(element_dict)
    else:
        element_dict = json.loads(text)
        return dict_to_elements(element_dict)


def flatten_dict(
    dictionary, parent_key="", separator="_", flatten_lists=False, keys_to_omit: List[str] = None
):
    """Flattens a nested dictionary into a single level dictionary. keys_to_omit is a list of keys
    that don't get flattened. If omitting a nested key, format as {parent_key}{separator}{key}.
    If flatten_lists is True, then lists are flattened as well."""
    keys_to_omit = keys_to_omit if keys_to_omit else []
    flattened_dict = {}
    for key, value in dictionary.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if new_key in keys_to_omit:
            flattened_dict[new_key] = value
        elif isinstance(value, dict):
            flattened_dict.update(
                flatten_dict(value, new_key, separator, flatten_lists, keys_to_omit=keys_to_omit),
            )
        elif isinstance(value, list) and flatten_lists:
            for index, item in enumerate(value):
                flattened_dict.update(
                    flatten_dict(
                        {f"{new_key}{separator}{index}": item},
                        "",
                        separator,
                        flatten_lists,
                        keys_to_omit=keys_to_omit,
                    )
                )
        else:
            flattened_dict[new_key] = value
    return flattened_dict


def _get_table_fieldnames(rows):
    table_fieldnames = list(TABLE_FIELDNAMES)
    for row in rows:
        metadata = row["metadata"]
        for key in flatten_dict(metadata):
            if key.startswith("regex_metadata") and key not in table_fieldnames:
                table_fieldnames.append(key)
    return table_fieldnames


def convert_to_isd_csv(elements: List[Element]) -> str:
    """
    Returns the representation of document elements as an Initial Structured Document (ISD)
    in CSV Format.
    """
    rows: List[Dict[str, Any]] = convert_to_isd(elements)
    table_fieldnames = _get_table_fieldnames(rows)
    # NOTE(robinson) - flatten metadata and add it to the table
    for row in rows:
        metadata = row.pop("metadata")
        for key, value in flatten_dict(metadata).items():
            if key in table_fieldnames:
                row[key] = value

        if row.get("sent_from"):
            row["sender"] = row.get("sent_from")
            if isinstance(row["sender"], list):
                row["sender"] = row["sender"][0]

    with io.StringIO() as buffer:
        csv_writer = csv.DictWriter(buffer, fieldnames=table_fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(rows)
        return buffer.getvalue()


def convert_to_csv(elements: List[Element]) -> str:
    """Converts a list of elements to a CSV."""
    return convert_to_isd_csv(elements)


@requires_dependencies(["pandas"])
def get_default_pandas_dtypes() -> dict:
    return {
        "text": pd.StringDtype(),
        "type": pd.StringDtype(),
        "element_id": pd.StringDtype(),
        "filename": pd.StringDtype(),  # Optional[str]
        "filetype": pd.StringDtype(),  # Optional[str]
        "file_directory": pd.StringDtype(),  # Optional[str]
        "last_modified": pd.StringDtype(),  # Optional[str]
        "attached_to_filename": pd.StringDtype(),  # Optional[str]
        "parent_id": pd.StringDtype(),  # Optional[str],
        "category_depth": "Int64",  # Optional[int]
        "image_path": pd.StringDtype(),  # Optional[str]
        "languages": object,  # Optional[List[str]]
        "page_number": "Int64",  # Optional[int]
        "page_name": pd.StringDtype(),  # Optional[str]
        "url": pd.StringDtype(),  # Optional[str]
        "link_urls": pd.StringDtype(),  # Optional[str]
        "link_texts": object,  # Optional[List[str]]
        "links": object,
        "sent_from": object,  # Optional[List[str]],
        "sent_to": object,  # Optional[List[str]]
        "subject": pd.StringDtype(),  # Optional[str]
        "section": pd.StringDtype(),  # Optional[str]
        "header_footer_type": pd.StringDtype(),  # Optional[str]
        "emphasized_text_contents": object,  # Optional[List[str]]
        "emphasized_text_tags": object,  # Optional[List[str]]
        "text_as_html": pd.StringDtype(),  # Optional[str]
        "regex_metadata": object,
        "max_characters": "Int64",  # Optional[int]
        "is_continuation": "boolean",  # Optional[bool]
        "detection_class_prob": float,  # Optional[float],
        "sender": pd.StringDtype(),
        "coordinates_points": object,
        "coordinates_system": pd.StringDtype(),
        "coordinates_layout_width": float,
        "coordinates_layout_height": float,
        "data_source_url": pd.StringDtype(),  # Optional[str]
        "data_source_version": pd.StringDtype(),  # Optional[str]
        "data_source_record_locator": object,
        "data_source_date_created": pd.StringDtype(),  # Optional[str]
        "data_source_date_modified": pd.StringDtype(),  # Optional[str]
        "data_source_date_processed": pd.StringDtype(),  # Optional[str]
        "data_source_permissions_data": object,
        "embeddings": object,
        "regex_metadata_key": object,
    }


@requires_dependencies(["pandas"])
def convert_to_dataframe(
    elements: List[Element],
    drop_empty_cols: bool = True,
    set_dtypes=False,
) -> "pd.DataFrame":
    """Converts document elements to a pandas DataFrame. The dataframe contains the
    following columns:
        text: the element text
        type: the text type (NarrativeText, Title, etc)

    Output is pd.DataFrame
    """
    elements_as_dict = convert_to_dict(elements)
    for d in elements_as_dict:
        if metadata := d.pop("metadata", None):
            d.update(flatten_dict(metadata, keys_to_omit=["data_source_record_locator"]))
    df = pd.DataFrame.from_dict(
        elements_as_dict,
    )
    if set_dtypes:
        dt = {k: v for k, v in get_default_pandas_dtypes().items() if k in df.columns}
        df = df.astype(dt)
    if drop_empty_cols:
        df.dropna(axis=1, how="all", inplace=True)
    return df


def filter_element_types(
    elements: List[Element],
    include_element_types: Optional[List[Element]] = None,
    exclude_element_types: Optional[List[Element]] = None,
) -> List[Element]:
    """Filters document elements by element type"""
    exactly_one(
        include_element_types=include_element_types,
        exclude_element_types=exclude_element_types,
    )

    filtered_elements: List[Element] = []
    if include_element_types:
        for element in elements:
            if type(element) in include_element_types:
                filtered_elements.append(element)

        return filtered_elements

    elif exclude_element_types:
        for element in elements:
            if type(element) not in exclude_element_types:
                filtered_elements.append(element)

        return filtered_elements

    return elements


def convert_to_coco(
    elements: List[Element],
    dataset_description: Optional[str] = None,
    dataset_version: str = "1.0",
    contributors: Tuple[str] = ("Unstructured Developers",),
) -> List[Dict[str, Any]]:
    coco_dataset = {}
    # Handle Info
    coco_dataset["info"] = {
        "description": (
            dataset_description
            if dataset_description
            else f"Unstructured COCO Dataset {datetime.now().strftime('%Y-%m-%d')}"
        ),
        "version": dataset_version,
        "year": datetime.now().year,
        "contributors": ",".join(contributors),
        "date_created": datetime.now().date().isoformat(),
    }
    elements_dict = convert_to_dict(elements)
    # Handle Images
    images = [
        {
            "width": (
                el["metadata"]["coordinates"]["layout_width"]
                if el["metadata"].get("coordinates")
                else None
            ),
            "height": (
                el["metadata"]["coordinates"]["layout_height"]
                if el["metadata"].get("coordinates")
                else None
            ),
            "file_directory": el["metadata"].get("file_directory", ""),
            "file_name": el["metadata"].get("filename", ""),
            "page_number": el["metadata"].get("page_number", ""),
        }
        for el in elements_dict
    ]
    images = list({tuple(sorted(d.items())): d for d in images}.values())
    for index, d in enumerate(images):
        d["id"] = index + 1
    coco_dataset["images"] = images
    # Handle Categories
    categories = sorted(set(TYPE_TO_TEXT_ELEMENT_MAP.keys()))
    categories = [{"id": i + 1, "name": cat} for i, cat in enumerate(categories)]
    coco_dataset["categories"] = categories
    # Handle Annotations
    annotations = [
        {
            "id": el["element_id"],
            "category_id": [x["id"] for x in categories if x["name"] == el["type"]][0],
            "bbox": [
                float(el["metadata"].get("coordinates")["points"][0][0]),
                float(el["metadata"].get("coordinates")["points"][0][1]),
                float(
                    abs(
                        el["metadata"].get("coordinates")["points"][0][0]
                        - el["metadata"].get("coordinates")["points"][2][0]
                    )
                ),
                float(
                    abs(
                        el["metadata"].get("coordinates")["points"][0][1]
                        - el["metadata"].get("coordinates")["points"][1][1]
                    )
                ),
            ]
            if el["metadata"].get("coordinates")
            else [],
            "area": (
                float(
                    abs(
                        el["metadata"].get("coordinates")["points"][0][0]
                        - el["metadata"].get("coordinates")["points"][2][0]
                    )
                )
                * float(
                    abs(
                        el["metadata"].get("coordinates")["points"][0][1]
                        - el["metadata"].get("coordinates")["points"][1][1]
                    )
                )
            )
            if el["metadata"].get("coordinates")
            else None,
        }
        for el in elements_dict
    ]
    coco_dataset["annotations"] = annotations
    return coco_dataset
