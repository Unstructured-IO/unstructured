import os

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pdf2image

from unstructured.documents.elements import PageBreak
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.xycut import bbox2points, recursive_xy_cut, vis_polygons_with_index


def run(pdf_path):
    images = pdf2image.convert_from_path(pdf_path)
    strategies = ["fast", "hi_res"]
    for strategy in strategies:
        run_partition_pdf(pdf_path, strategy, images)


def run_partition_pdf(pdf_path, strategy, images):
    output_dir = os.path.join(output_root_dir, strategy)
    os.makedirs(output_dir, exist_ok=True)

    elements = partition_pdf(
        filename=pdf_path,
        strategy=strategy,
        include_page_breaks=True,
    )

    elements_coordinates = []
    page_elements_coordinates = []
    for el in elements:
        if isinstance(el, PageBreak):
            if page_elements_coordinates:
                elements_coordinates.append(page_elements_coordinates)
                page_elements_coordinates = []
        else:
            page_elements_coordinates.append(el.metadata.coordinates)

    # After the loop, handle any remaining coordinates
    if page_elements_coordinates:
        elements_coordinates.append(page_elements_coordinates)

    assert len(images) == len(elements_coordinates)
    for idx, (img, elements_coordinates_per_page) in enumerate(zip(images, elements_coordinates)):
        page_idx = idx + 1
        output_image_name = os.path.splitext(os.path.basename(pdf_path))[0]
        image = np.array(img)
        image_height, image_width, _ = image.shape
        boxes = []
        for coordinate in elements_coordinates_per_page:
            points = coordinate.points
            w = coordinate.system.width
            h = coordinate.system.height
            _left, _top = points[0]
            _right, _bottom = points[2]
            left = _left * image_width / w
            right = _right * image_width / w
            top = _top * image_height / h
            bottom = _bottom * image_height / h
            boxes.append([int(left), int(top), int(right), int(bottom)])

        annotated_original_image = vis_polygons_with_index(image, [bbox2points(it) for it in boxes])
        cv2.imwrite(os.path.join(output_dir, f"{output_image_name}_{page_idx}_original.jpg"), annotated_original_image)

        res = []
        recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
        assert len(res) == len(boxes)
        np_array_boxes = np.array(boxes)
        sorted_boxes = np_array_boxes[np.array(res)].tolist()

        annotated_result_image = vis_polygons_with_index(image, [bbox2points(it) for it in sorted_boxes])
        cv2.imwrite(os.path.join(output_dir, f"{output_image_name}_{page_idx}_result.jpg"), annotated_result_image)


def show_plot(result_image, original_image, desired_width):
    if desired_width:
        # Calculate the desired height based on the original aspect ratio
        aspect_ratio = original_image.width / original_image.height
        desired_height = desired_width / aspect_ratio

        # Create a figure with the desired size and aspect ratio
        fig, ax = plt.subplots(figsize=(desired_width, desired_height))
    else:
        # Create figure and axes
        fig, ax = plt.subplots()
    # Display the image
    ax.imshow(result_image)
    plt.show()


if __name__ == '__main__':
    cur_dir = os.getcwd()
    base_dir = os.path.join(cur_dir, os.pardir, os.pardir)
    example_docs_dir = os.path.join(base_dir, "example-docs")
    output_root_dir = os.path.join(cur_dir, "output")
    os.makedirs(output_root_dir, exist_ok=True)

    f_path = os.path.join(example_docs_dir, "multi-column-2p.pdf")

    run(f_path)
