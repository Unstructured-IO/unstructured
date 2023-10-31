import os
import sys

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pdf2image
from PIL import Image

from unstructured.documents.elements import PageBreak
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_DONT, SORT_MODE_XY_CUT
from unstructured.partition.utils.xycut import (
    bbox2points,
    recursive_xy_cut,
    vis_polygons_with_index,
)


def show_plot(image, desired_width=None):
    image_height, image_width, _ = image.shape
    if desired_width:
        # Calculate the desired height based on the original aspect ratio
        aspect_ratio = image_width / image_height
        desired_height = desired_width / aspect_ratio

        # Create a figure with the desired size and aspect ratio
        fig, ax = plt.subplots(figsize=(desired_width, desired_height))
    else:
        # Create figure and axes
        fig, ax = plt.subplots()
    # Display the image
    ax.imshow(image)
    plt.show()


def extract_element_coordinates(elements):
    elements_coordinates = []
    page_elements_coordinates = []

    for el in elements:
        if isinstance(el, PageBreak) and page_elements_coordinates:
            elements_coordinates.append(page_elements_coordinates)
            page_elements_coordinates = []
        else:
            page_elements_coordinates.append(el.metadata.coordinates)

    if page_elements_coordinates:
        elements_coordinates.append(page_elements_coordinates)

    return elements_coordinates


def convert_coordinates_to_boxes(coordinates, image):
    boxes = []

    for coordinate in coordinates:
        if not coordinate:
            continue

        points = coordinate.points
        _left, _top = points[0]
        _right, _bottom = points[2]
        w = coordinate.system.width
        h = coordinate.system.height
        image_height, image_width, _ = image.shape
        left = _left * image_width / w
        right = _right * image_width / w
        top = _top * image_height / h
        bottom = _bottom * image_height / h
        boxes.append([int(left), int(top), int(right), int(bottom)])

    return boxes


def order_boxes(boxes):
    res = []
    recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
    np_array_boxes = np.array(boxes)
    ordered_boxes = np_array_boxes[np.array(res)].tolist()
    return ordered_boxes


def draw_boxes(image, boxes, output_dir, base_name, page_num, output_type, label):
    annotated_image = vis_polygons_with_index(image, [bbox2points(it) for it in boxes])

    if output_type in ["plot", "all"]:
        print(f"{label} elements - Page: {page_num}")
        show_plot(annotated_image, desired_width=20)

    if output_type in ["image", "all"]:
        output_image_path = os.path.join(output_dir, f"{base_name}_{page_num}_{label}.jpg")
        cv2.imwrite(output_image_path, annotated_image)


def draw_elements(elements, images, output_type, output_dir, base_name, label):
    elements_coordinates = extract_element_coordinates(elements)

    assert len(images) == len(elements_coordinates)
    for idx, (img, coords_per_page) in enumerate(zip(images, elements_coordinates)):
        image = np.array(img)
        boxes = convert_coordinates_to_boxes(coords_per_page, image)
        if len(boxes) < len(coords_per_page):
            delta = len(coords_per_page) - len(boxes)
            print(f"{delta} elements in page {idx+1} do not have coordinate data")
        draw_boxes(image, boxes, output_dir, base_name, idx + 1, output_type, label)


def run_partition_pdf(
    f_path,
    strategy,
    sort_mode,
    filetype,
    output_type="plot",
    output_root_dir="",
):
    print(
        f">>> Starting run_partition_pdf - f_path: {f_path} - strategy: {strategy} "
        f"- sort_mode: {sort_mode} - filetype: {filetype}",
    )
    f_base_name = os.path.splitext(os.path.basename(f_path))[0]

    output_dir = os.path.join(output_root_dir, strategy, f_base_name)
    os.makedirs(output_dir, exist_ok=True)

    is_image = filetype == "image"

    images = [Image.open(f_path)] if is_image else pdf2image.convert_from_path(f_path)

    ordered_elements = partition_pdf(
        filename=f_path,
        strategy=strategy,
        include_page_breaks=True,
        sort_mode=sort_mode,
        is_image=is_image,
    )
    print("\n\n".join([str(el) for el in ordered_elements]))

    draw_elements(ordered_elements, images, output_type, output_dir, f_base_name, sort_mode)

    print("<<< Finished run_partition_pdf")


def run():
    f_sub_path = sys.argv[1]
    strategy = sys.argv[2]
    sort_mode = sys.argv[3]
    filetype = sys.argv[4]

    base_dir = os.getcwd()
    output_root_dir = os.path.join(base_dir, "examples", "custom-layout-order", "output")
    os.makedirs(output_root_dir, exist_ok=True)

    f_path = os.path.join(base_dir, f_sub_path)
    run_partition_pdf(f_path, strategy, sort_mode, filetype, "image", output_root_dir)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Please provide the path to the file name as the first argument, the strategy as the "
            "second argument, the sort_mode as the third argument, and the filetype as fourth "
            "argument.",
        )
        sys.exit(1)

    if sys.argv[3] not in [SORT_MODE_XY_CUT, SORT_MODE_BASIC, SORT_MODE_DONT]:
        print("Invalid sort mode! The sort mode should be `xy-cut`, `basic`, or `dont`")
        sys.exit(1)

    if sys.argv[4] not in ["pdf", "image"]:
        print("Invalid filetype! The filetype should be eiter `pdf` or `image`")
        sys.exit(1)

    run()
