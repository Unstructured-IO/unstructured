import os
import pathlib
import sys

import pdf2image
from unstructured_inference.inference.elements import Rectangle
from unstructured_inference.visualize import draw_bbox

from unstructured.documents.elements import PageBreak
from unstructured.partition.pdf import partition_pdf

CUR_DIR = pathlib.Path(__file__).parent.resolve()


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


def run_partition_pdf(f_path, strategy, images, output_dir):
    elements = partition_pdf(
        f_path,
        strategy=strategy,
        include_page_breaks=True,
    )

    elements_coordinates = extract_element_coordinates(elements)
    assert len(images) == len(elements_coordinates)

    for idx, (img, coords_per_page) in enumerate(zip(images, elements_coordinates)):
        for coordinate in coords_per_page:
            points = coordinate.points
            x1, y1 = points[0]
            x2, y2 = points[2]
            rect = Rectangle(x1, y1, x2, y2)
            img = draw_bbox(img, rect, color="red")

        output_image_path = os.path.join(output_dir, f"{strategy}-{idx + 1}.jpg")
        print(f"output_image_path: {output_image_path}")

        img.save(output_image_path)


def run(f_path, strategy):
    f_basename = os.path.splitext(os.path.basename(f_path))[0]
    output_dir_path = os.path.join(output_basedir_path, f_basename)
    os.makedirs(output_dir_path, exist_ok=True)

    images = pdf2image.convert_from_path(f_path)
    run_partition_pdf(f_path, strategy, images, output_dir_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Please provide the path to the file name as the first argument "
            "and the strategy as the second argument.",
        )
        sys.exit(1)

    if sys.argv[2] not in ["auto", "hi_res", "ocr_only", "fast"]:
        print("Invalid strategy")
        sys.exit(1)

    output_basedir_path = os.path.join(CUR_DIR, "output")
    os.makedirs(output_basedir_path, exist_ok=True)

    run(f_path=sys.argv[1], strategy=sys.argv[2])
