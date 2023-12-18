import os
import pathlib
import sys

import pdf2image
from PIL import Image
from unstructured_inference.inference.elements import TextRegion
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


def run_partition_pdf(f_path, strategy, images, output_dir, output_f_basename, is_image):
    elements = partition_pdf(
        f_path,
        strategy=strategy,
        is_image=is_image,
        include_page_breaks=True,
        analysis=True,
        analyzed_image_output_dir_path=output_dir,
    )

    elements_coordinates = extract_element_coordinates(elements)
    assert len(images) == len(elements_coordinates)

    for idx, (img, coords_per_page) in enumerate(zip(images, elements_coordinates)):
        for coordinate in coords_per_page:
            points = coordinate.points
            x1, y1 = points[0]
            x2, y2 = points[2]
            el = TextRegion.from_coords(x1, y1, x2, y2)
            img = draw_bbox(img, el, color="red")

        output_image_path = os.path.join(output_dir, f"{output_f_basename}_{idx + 1}_final.jpg")
        img.save(output_image_path)
        print(f"output_image_path: {output_image_path}")


def run(f_path, strategy, document_type):
    f_basename = os.path.splitext(os.path.basename(f_path))[0]
    output_dir_path = os.path.join(output_basedir_path, f_basename)
    os.makedirs(output_dir_path, exist_ok=True)

    is_image = document_type == "image"
    if is_image:
        with Image.open(f_path) as img:
            img = img.convert("RGB")
            images = [img]
    else:
        images = pdf2image.convert_from_path(f_path)

    run_partition_pdf(f_path, strategy, images, output_dir_path, f_basename, is_image)


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

    if sys.argv[3] not in ["pdf", "image"]:
        print("Invalid document type")
        sys.exit(1)

    output_basedir_path = os.path.join(CUR_DIR, "output")
    os.makedirs(output_basedir_path, exist_ok=True)

    run(f_path=sys.argv[1], strategy=sys.argv[2], document_type=sys.argv[3])
