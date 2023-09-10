# coding: utf-8
import os
from pathlib import Path
from typing import List

import torch
from PIL import Image
from unstructured_inference.models.tables import (
    UnstructuredTableTransformerModel,
    get_class_map,
    outputs_to_objects,
)
from unstructured_inference.visualize import ImageDraw

from unstructured.partition.pdf import partition_pdf_or_image

str_class_name2idx = get_class_map("structure")
str_class_idx2name = {v: k for k, v in str_class_name2idx.items()}
model = UnstructuredTableTransformerModel()
model.initialize("microsoft/table-transformer-structure-recognition")
element_to_color = {
    "table": "black",
    "table row": "red",
    "table column": "green",
    "table spanning cell": "blue",
    "ocr": "yellow",
}


def simple_draw_box(image, bbox, color):
    image = image.copy()
    draw = ImageDraw(image)
    topleft = (bbox[0], bbox[1])
    bottomright = (bbox[2], bbox[3])
    draw.rectangle((topleft, bottomright), outline=color, width=2)
    return image


def show_tokens_on_image(img, tokens):
    for token in tokens:
        img = simple_draw_box(
            img,
            token["bbox"],
            element_to_color.get(token.get("label", ""), "black"),
        )
    img.show()
    return img


def show_structure_on_image(img, model):
    if hasattr(model, "get_structure"):
        structure = model.get_structure(img)
    else:
        with torch.no_grad():
            encoding = model.feature_extractor(img, return_tensors="pt").to(model.device)
            structure = model.model(**encoding)

    objs = outputs_to_objects(structure, img.size, str_class_idx2name)
    tokens = model.get_tokens(img)
    for token in tokens:
        token["label"] = "ocr"
    return show_tokens_on_image(img, objs + tokens)


def get_box_from_image_file_with_model(image_file, model):
    elements = partition_pdf_or_image(
        filename=image_file,
        strategy="hi_res",
        model_name=model,
        infer_table_structure=True,
        is_image=True,
    )
    table_bbs = [ele.metadata.coordinates for ele in elements if ele.category == "Table"]
    return [
        (coord.points[0][0], coord.points[0][1], coord.points[2][0], coord.points[2][1])
        for coord in table_bbs
    ]


def pad_image_with_background(image, pad=10, background=None):
    width, height = image.size
    background = background or "white"
    new = Image.new(image.mode, (width + pad, height + pad), background)
    new.paste(image, (pad // 2, pad // 2))
    return new


def main(img_files: List[str], output_folder: str, experiment_name: str):
    root_path = Path(output_folder) / experiment_name
    os.makedirs(root_path, exist_ok=True)

    for img_file in img_files:
        image = Image.open(img_file)

        # first try just throw the whole image/page into the model
        annotated = show_structure_on_image(image, model)
        annotated.save(root_path / f"{os.path.basename(img_file)}-model-output-annotated.png")
        # finish all the computes (align elements to get structure, merge with ocr, etc) and write
        # the html
        with open(root_path / f"{os.path.basename(img_file)}.html", "w") as fp:
            fp.write(model.run_prediction(image))

        # now use yolox to detect tables first then crop the tables and run inference on the crop
        boxes = get_box_from_image_file_with_model(img_file, "yolox")

        buffer = 12
        for i, box in enumerate(boxes):
            crop = image.crop((box[0] - buffer, box[1] - buffer, box[2] + buffer, box[3] + buffer))
            # overlay direct output from structure detection model
            annotated = show_structure_on_image(crop, model)
            annotated.save(
                root_path / f"{os.path.basename(img_file)}-box{i}-model-output-annotated.png",
            )
            with open(root_path / f"{os.path.basename(img_file)}-box{i}.html", "w") as fp:
                fp.write(model.run_prediction(crop))


if __name__ == "__main__":
    img_files = [
        "example-docs/full-page-table.png",
        "example-docs/compound-header-table.png",
    ]

    main(img_files, "/tmp", "test")
