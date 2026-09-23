# https://github.com/microsoft/table-transformer/blob/main/src/postprocess.py
"""
Copyright (C) 2021 Microsoft Corporation
"""

from collections import defaultdict


class Rect:
    def __init__(self, bbox=None):
        if bbox is None:
            self.x_min = 0
            self.y_min = 0
            self.x_max = 0
            self.y_max = 0
        else:
            self.x_min = bbox[0]
            self.y_min = bbox[1]
            self.x_max = bbox[2]
            self.y_max = bbox[3]

    def get_area(self):
        """Calculates the area of the rectangle"""
        area = (self.x_max - self.x_min) * (self.y_max - self.y_min)
        return area if area > 0 else 0.0

    def intersect(self, other):
        """Calculates the intersection with another rectangle"""
        if self.get_area() == 0:
            self.x_min = other.x_min
            self.y_min = other.y_min
            self.x_max = other.x_max
            self.y_max = other.y_max
        else:
            self.x_min = max(self.x_min, other.x_min)
            self.y_min = max(self.y_min, other.y_min)
            self.x_max = min(self.x_max, other.x_max)
            self.y_max = min(self.y_max, other.y_max)

            if self.x_min > self.x_max or self.y_min > self.y_max or self.get_area() == 0:
                self.x_min = 0
                self.y_min = 0
                self.x_max = 0
                self.y_max = 0

        return self

    def include_rect(self, bbox):
        """Calculates a rectangle that includes both rectangles"""
        other = Rect(bbox)

        if self.get_area() == 0:
            self.x_min = other.x_min
            self.y_min = other.y_min
            self.x_max = other.x_max
            self.y_max = other.y_max
            return self

        self.x_min = min(self.x_min, other.x_min)
        self.y_min = min(self.y_min, other.y_min)
        self.x_max = max(self.x_max, other.x_max)
        self.y_max = max(self.y_max, other.y_max)

        # if self.get_area() == 0:
        #     self.x_min = other.x_min
        #     self.y_min = other.y_min
        #     self.x_max = other.x_max
        #     self.y_max = other.y_max

        return self

    def get_bbox(self):
        """Returns the coordinates that define the rectangle"""
        return [self.x_min, self.y_min, self.x_max, self.y_max]


def apply_threshold(objects, threshold):
    """
    Filter out objects below a certain score.
    """
    return [obj for obj in objects if obj["score"] >= threshold]


def refine_rows(rows, tokens, score_threshold):
    """
    Apply operations to the detected rows, such as
    thresholding, NMS, and alignment.
    """

    if len(tokens) > 0:
        rows = nms_by_containment(rows, tokens, overlap_threshold=0.5)
        remove_objects_without_content(tokens, rows)
    else:
        rows = nms(rows, match_criteria="object2_overlap", match_threshold=0.5, keep_higher=True)
    if len(rows) > 1:
        rows = sort_objects_top_to_bottom(rows)

    return rows


def refine_columns(columns, tokens, score_threshold):
    """
    Apply operations to the detected columns, such as
    thresholding, NMS, and alignment.
    """

    if len(tokens) > 0:
        columns = nms_by_containment(columns, tokens, overlap_threshold=0.5)
        remove_objects_without_content(tokens, columns)
    else:
        columns = nms(
            columns,
            match_criteria="object2_overlap",
            match_threshold=0.25,
            keep_higher=True,
        )
    if len(columns) > 1:
        columns = sort_objects_left_to_right(columns)

    return columns


def nms_by_containment(container_objects, package_objects, overlap_threshold=0.5):
    """
    Non-maxima suppression (NMS) of objects based on shared containment of other objects.
    """
    container_objects = sort_objects_by_score(container_objects)
    num_objects = len(container_objects)
    suppression = [False for obj in container_objects]

    packages_by_container, _, _ = slot_into_containers(
        container_objects,
        package_objects,
        overlap_threshold=overlap_threshold,
        forced_assignment=False,
    )

    for object2_num in range(1, num_objects):
        object2_packages = set(packages_by_container[object2_num])
        if len(object2_packages) == 0:
            suppression[object2_num] = True
        for object1_num in range(object2_num):
            if not suppression[object1_num]:
                object1_packages = set(packages_by_container[object1_num])
                if len(object2_packages.intersection(object1_packages)) > 0:
                    suppression[object2_num] = True

    final_objects = [obj for idx, obj in enumerate(container_objects) if not suppression[idx]]
    return final_objects


def slot_into_containers(
    container_objects,
    package_objects,
    overlap_threshold=0.5,
    forced_assignment=False,
):
    """
    Slot a collection of objects into the container they occupy most (the container which holds the
    largest fraction of the object).
    """
    best_match_scores = []

    container_assignments = [[] for container in container_objects]
    package_assignments = [[] for package in package_objects]

    if len(container_objects) == 0 or len(package_objects) == 0:
        return container_assignments, package_assignments, best_match_scores

    match_scores = defaultdict(dict)
    for package_num, package in enumerate(package_objects):
        match_scores = []
        package_rect = Rect(package["bbox"])
        package_area = package_rect.get_area()
        for container_num, container in enumerate(container_objects):
            container_rect = Rect(container["bbox"])
            intersect_area = container_rect.intersect(Rect(package["bbox"])).get_area()

            if package_area > 0:
                overlap_fraction = intersect_area / package_area

                match_scores.append(
                    {
                        "container": container,
                        "container_num": container_num,
                        "score": overlap_fraction,
                    },
                )

        if len(match_scores) > 0:
            sorted_match_scores = sort_objects_by_score(match_scores)

            best_match_score = sorted_match_scores[0]
            best_match_scores.append(best_match_score["score"])
            if forced_assignment or best_match_score["score"] >= overlap_threshold:
                container_assignments[best_match_score["container_num"]].append(package_num)
                package_assignments[package_num].append(best_match_score["container_num"])

    return container_assignments, package_assignments, best_match_scores


def sort_objects_by_score(objects, reverse=True):
    """
    Put any set of objects in order from high score to low score.
    """
    return sorted(objects, key=lambda k: k["score"], reverse=reverse)


def remove_objects_without_content(page_spans, objects):
    """
    Remove any objects (these can be rows, columns, supercells, etc.) that don't
    have any text associated with them.
    """
    for obj in objects[:]:
        object_text, _ = extract_text_inside_bbox(page_spans, obj["bbox"])
        if len(object_text.strip()) == 0:
            objects.remove(obj)


def extract_text_inside_bbox(spans, bbox):
    """
    Extract the text inside a bounding box.
    """
    bbox_spans = get_bbox_span_subset(spans, bbox)
    bbox_text = extract_text_from_spans(bbox_spans, remove_integer_superscripts=True)

    return bbox_text, bbox_spans


def get_bbox_span_subset(spans, bbox, threshold=0.5):
    """
    Reduce the set of spans to those that fall within a bounding box.

    threshold: the fraction of the span that must overlap with the bbox.
    """
    span_subset = []
    for span in spans:
        if overlaps(span["bbox"], bbox, threshold):
            span_subset.append(span)
    return span_subset


def overlaps(bbox1, bbox2, threshold=0.5):
    """
    Test if more than "threshold" fraction of bbox1 overlaps with bbox2.
    """
    rect1 = Rect(list(bbox1))
    area1 = rect1.get_area()
    if area1 == 0:
        return False
    return rect1.intersect(Rect(list(bbox2))).get_area() / area1 >= threshold


def extract_text_from_spans(spans, join_with_space=True, remove_integer_superscripts=True):
    """
    Convert a collection of page tokens/words/spans into a single text string.
    """

    join_char = " " if join_with_space else ""
    spans_copy = spans[:]

    if remove_integer_superscripts:
        for span in spans:
            if "flags" not in span:
                continue
            flags = span["flags"]
            if flags & 2**0:  # superscript flag
                if span["text"].strip().isdigit():
                    spans_copy.remove(span)
                else:
                    span["superscript"] = True

    if len(spans_copy) == 0:
        return ""

    spans_copy.sort(key=lambda span: span["span_num"])
    spans_copy.sort(key=lambda span: span["line_num"])
    spans_copy.sort(key=lambda span: span["block_num"])

    # Force the span at the end of every line within a block to have exactly one space
    # unless the line ends with a space or ends with a non-space followed by a hyphen
    line_texts = []
    line_span_texts = [spans_copy[0]["text"]]
    for span1, span2 in zip(spans_copy[:-1], spans_copy[1:]):
        if span1["block_num"] != span2["block_num"] or span1["line_num"] != span2["line_num"]:
            line_text = join_char.join(line_span_texts).strip()
            if (
                len(line_text) > 0
                and line_text[-1] != " "
                and not (len(line_text) > 1 and line_text[-1] == "-" and line_text[-2] != " ")
                and not join_with_space
            ):
                line_text += " "
            line_texts.append(line_text)
            line_span_texts = [span2["text"]]
        else:
            line_span_texts.append(span2["text"])
    line_text = join_char.join(line_span_texts)
    line_texts.append(line_text)

    return join_char.join(line_texts).strip()


def sort_objects_left_to_right(objs):
    """
    Put the objects in order from left to right.
    """
    return sorted(objs, key=lambda k: k["bbox"][0] + k["bbox"][2])


def sort_objects_top_to_bottom(objs):
    """
    Put the objects in order from top to bottom.
    """
    return sorted(objs, key=lambda k: k["bbox"][1] + k["bbox"][3])


def align_columns(columns, bbox):
    """
    For every column, align the top and bottom boundaries to the final
    table bounding box.
    """
    try:
        for column in columns:
            column["bbox"][1] = bbox[1]
            column["bbox"][3] = bbox[3]
    except Exception as err:
        print(f"Could not align columns: {err}")
        pass

    return columns


def align_rows(rows, bbox):
    """
    For every row, align the left and right boundaries to the final
    table bounding box.
    """
    try:
        for row in rows:
            row["bbox"][0] = bbox[0]
            row["bbox"][2] = bbox[2]
    except Exception as err:
        print(f"Could not align rows: {err}")
        pass

    return rows


def nms(objects, match_criteria="object2_overlap", match_threshold=0.05, keep_higher=True):
    """
    A customizable version of non-maxima suppression (NMS).

    Default behavior: If a lower-confidence object overlaps more than 5% of its area
    with a higher-confidence object, remove the lower-confidence object.

    objects: set of dicts; each object dict must have a 'bbox' and a 'score' field
    match_criteria: how to measure how much two objects "overlap"
    match_threshold: the cutoff for determining that overlap requires suppression of one object
    keep_higher: if True, keep the object with the higher metric; otherwise, keep the lower
    """
    if len(objects) == 0:
        return []

    objects = sort_objects_by_score(objects, reverse=keep_higher)

    num_objects = len(objects)
    suppression = [False for obj in objects]

    for object2_num in range(1, num_objects):
        object2_rect = Rect(objects[object2_num]["bbox"])
        object2_area = object2_rect.get_area()
        for object1_num in range(object2_num):
            if not suppression[object1_num]:
                object1_rect = Rect(objects[object1_num]["bbox"])
                object1_area = object1_rect.get_area()
                intersect_area = object1_rect.intersect(object2_rect).get_area()
                try:
                    if match_criteria == "object1_overlap":
                        metric = intersect_area / object1_area
                    elif match_criteria == "object2_overlap":
                        metric = intersect_area / object2_area
                    elif match_criteria == "iou":
                        metric = intersect_area / (object1_area + object2_area - intersect_area)
                    if metric >= match_threshold:
                        suppression[object2_num] = True
                        break
                except ZeroDivisionError:
                    # Intended to recover from divide-by-zero
                    pass

    return [obj for idx, obj in enumerate(objects) if not suppression[idx]]


def align_supercells(supercells, rows, columns):
    """
    For each supercell, align it to the rows it intersects 50% of the height of,
    and the columns it intersects 50% of the width of.
    Eliminate supercells for which there are no rows and columns it intersects 50% with.
    """
    aligned_supercells = []

    for supercell in supercells:
        supercell["header"] = False
        row_bbox_rect = None
        col_bbox_rect = None
        intersecting_header_rows = set()
        intersecting_data_rows = set()
        for row_num, row in enumerate(rows):
            row_height = row["bbox"][3] - row["bbox"][1]
            supercell_height = supercell["bbox"][3] - supercell["bbox"][1]
            min_row_overlap = max(row["bbox"][1], supercell["bbox"][1])
            max_row_overlap = min(row["bbox"][3], supercell["bbox"][3])
            overlap_height = max_row_overlap - min_row_overlap
            if "span" in supercell:
                overlap_fraction = max(
                    overlap_height / row_height,
                    overlap_height / supercell_height,
                )
            else:
                overlap_fraction = overlap_height / row_height
            if overlap_fraction >= 0.5:
                if "header" in row and row["header"]:
                    intersecting_header_rows.add(row_num)
                else:
                    intersecting_data_rows.add(row_num)

        # Supercell cannot span across the header boundary; eliminate whichever
        # group of rows is the smallest
        supercell["header"] = False
        if len(intersecting_data_rows) > 0 and len(intersecting_header_rows) > 0:
            if len(intersecting_data_rows) > len(intersecting_header_rows):
                intersecting_header_rows = set()
            else:
                intersecting_data_rows = set()
        if len(intersecting_header_rows) > 0:
            supercell["header"] = True
        elif "span" in supercell:
            continue  # Require span supercell to be in the header
        intersecting_rows = intersecting_data_rows.union(intersecting_header_rows)
        # Determine vertical span of aligned supercell
        for row_num in intersecting_rows:
            if row_bbox_rect is None:
                row_bbox_rect = Rect(rows[row_num]["bbox"])
            else:
                row_bbox_rect = row_bbox_rect.include_rect(rows[row_num]["bbox"])
        if row_bbox_rect is None:
            continue

        intersecting_cols = []
        for col_num, col in enumerate(columns):
            col_width = col["bbox"][2] - col["bbox"][0]
            supercell_width = supercell["bbox"][2] - supercell["bbox"][0]
            min_col_overlap = max(col["bbox"][0], supercell["bbox"][0])
            max_col_overlap = min(col["bbox"][2], supercell["bbox"][2])
            overlap_width = max_col_overlap - min_col_overlap
            if "span" in supercell:
                overlap_fraction = max(overlap_width / col_width, overlap_width / supercell_width)
                # Multiply by 2 effectively lowers the threshold to 0.25
                if supercell["header"]:
                    overlap_fraction = overlap_fraction * 2
            else:
                overlap_fraction = overlap_width / col_width
            if overlap_fraction >= 0.5:
                intersecting_cols.append(col_num)
                if col_bbox_rect is None:
                    col_bbox_rect = Rect(col["bbox"])
                else:
                    col_bbox_rect = col_bbox_rect.include_rect(col["bbox"])
        if col_bbox_rect is None:
            continue

        supercell_bbox = row_bbox_rect.intersect(col_bbox_rect).get_bbox()
        supercell["bbox"] = supercell_bbox

        # Only a true supercell if it joins across multiple rows or columns
        if (
            len(intersecting_rows) > 0
            and len(intersecting_cols) > 0
            and (len(intersecting_rows) > 1 or len(intersecting_cols) > 1)
        ):
            supercell["row_numbers"] = list(intersecting_rows)
            supercell["column_numbers"] = intersecting_cols
            aligned_supercells.append(supercell)

            # A span supercell in the header means there must be supercells above it in the header
            if "span" in supercell and supercell["header"] and len(supercell["column_numbers"]) > 1:
                for row_num in range(0, min(supercell["row_numbers"])):
                    new_supercell = {
                        "row_numbers": [row_num],
                        "column_numbers": supercell["column_numbers"],
                        "score": supercell["score"],
                        "propagated": True,
                    }
                    new_supercell_columns = [columns[idx] for idx in supercell["column_numbers"]]
                    new_supercell_rows = [rows[idx] for idx in supercell["row_numbers"]]
                    bbox = [
                        min([column["bbox"][0] for column in new_supercell_columns]),
                        min([row["bbox"][1] for row in new_supercell_rows]),
                        max([column["bbox"][2] for column in new_supercell_columns]),
                        max([row["bbox"][3] for row in new_supercell_rows]),
                    ]
                    new_supercell["bbox"] = bbox
                    aligned_supercells.append(new_supercell)

    return aligned_supercells


def nms_supercells(supercells):
    """
    A NMS scheme for supercells that first attempts to shrink supercells to
    resolve overlap.
    If two supercells overlap the same (sub)cell, shrink the lower confidence
    supercell to resolve the overlap. If shrunk supercell is empty, remove it.
    """

    supercells = sort_objects_by_score(supercells)
    num_supercells = len(supercells)
    suppression = [False for supercell in supercells]

    for supercell2_num in range(1, num_supercells):
        supercell2 = supercells[supercell2_num]
        for supercell1_num in range(supercell2_num):
            supercell1 = supercells[supercell1_num]
            remove_supercell_overlap(supercell1, supercell2)
        if (
            (len(supercell2["row_numbers"]) < 2 and len(supercell2["column_numbers"]) < 2)
            or len(supercell2["row_numbers"]) == 0
            or len(supercell2["column_numbers"]) == 0
        ):
            suppression[supercell2_num] = True

    return [obj for idx, obj in enumerate(supercells) if not suppression[idx]]


def header_supercell_tree(supercells):
    """
    Make sure no supercell in the header is below more than one supercell in any row above it.
    The cells in the header form a tree, but a supercell with more than one supercell in a row
    above it means that some cell has more than one parent, which is not allowed. Eliminate
    any supercell that would cause this to be violated.
    """
    header_supercells = [
        supercell for supercell in supercells if "header" in supercell and supercell["header"]
    ]
    header_supercells = sort_objects_by_score(header_supercells)

    for header_supercell in header_supercells[:]:
        ancestors_by_row = defaultdict(int)
        min_row = min(header_supercell["row_numbers"])
        for header_supercell2 in header_supercells:
            max_row2 = max(header_supercell2["row_numbers"])
            if max_row2 < min_row and set(header_supercell["column_numbers"]).issubset(
                set(header_supercell2["column_numbers"]),
            ):
                for row2 in header_supercell2["row_numbers"]:
                    ancestors_by_row[row2] += 1
        for row in range(0, min_row):
            if ancestors_by_row[row] != 1:
                supercells.remove(header_supercell)
                break


def remove_supercell_overlap(supercell1, supercell2):
    """
    This function resolves overlap between supercells (supercells must be
    disjoint) by iteratively shrinking supercells by the fewest grid cells
    necessary to resolve the overlap.
    Example:
    If two supercells overlap at grid cell (R, C), and supercell #1 is less
    confident than supercell #2, we eliminate either row R from supercell #1
    or column C from supercell #1 by comparing the number of columns in row R
    versus the number of rows in column C. If the number of columns in row R
    is less than the number of rows in column C, we eliminate row R from
    supercell #1. This resolves the overlap by removing fewer grid cells from
    supercell #1 than if we eliminated column C from it.
    """
    common_rows = set(supercell1["row_numbers"]).intersection(set(supercell2["row_numbers"]))
    common_columns = set(supercell1["column_numbers"]).intersection(
        set(supercell2["column_numbers"]),
    )

    # While the supercells have overlapping grid cells, continue shrinking the less-confident
    # supercell one row or one column at a time
    while len(common_rows) > 0 and len(common_columns) > 0:
        # Try to shrink the supercell as little as possible to remove the overlap;
        # if the supercell has fewer rows than columns, remove an overlapping column,
        # because this removes fewer grid cells from the supercell;
        # otherwise remove an overlapping row
        if len(supercell2["row_numbers"]) < len(supercell2["column_numbers"]):
            min_column = min(supercell2["column_numbers"])
            max_column = max(supercell2["column_numbers"])
            if max_column in common_columns:
                common_columns.remove(max_column)
                supercell2["column_numbers"].remove(max_column)
            elif min_column in common_columns:
                common_columns.remove(min_column)
                supercell2["column_numbers"].remove(min_column)
            else:
                supercell2["column_numbers"] = []
                common_columns = set()
        else:
            min_row = min(supercell2["row_numbers"])
            max_row = max(supercell2["row_numbers"])
            if max_row in common_rows:
                common_rows.remove(max_row)
                supercell2["row_numbers"].remove(max_row)
            elif min_row in common_rows:
                common_rows.remove(min_row)
                supercell2["row_numbers"].remove(min_row)
            else:
                supercell2["row_numbers"] = []
                common_rows = set()
