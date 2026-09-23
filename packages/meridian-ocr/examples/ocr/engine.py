import os
import re
import time
from typing import List, cast

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from unstructured_inference.inference import layout
from unstructured_inference.inference.elements import Rectangle, TextRegion


def remove_non_printable(s):
    dst_str = re.sub(r"[^\x20-\x7E]", " ", s)
    return " ".join(dst_str.split())


def run_ocr_with_layout_detection(
    images,
    detection_model=None,
    element_extraction_model=None,
    mode="individual_blocks",
    output_dir="",
    drawable=True,
    printable=True,
):
    total_text_extraction_infer_time = 0
    total_extracted_text = {}
    for i, image in enumerate(images):
        page_num = i + 1
        page_num_str = f"page{page_num}"

        page = layout.PageLayout(
            number=i + 1,
            image=image,
            layout=None,
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
        )

        inferred_layout: List[TextRegion] = cast(List[TextRegion], page.detection_model(page.image))

        cv_img = np.array(image)

        if mode == "individual_blocks":
            # OCR'ing individual blocks (current approach)
            text_extraction_start_time = time.time()

            elements = page.get_elements_from_layout(inferred_layout)

            text_extraction_infer_time = time.time() - text_extraction_start_time

            total_text_extraction_infer_time += text_extraction_infer_time

            page_text = ""
            for el in elements:
                page_text += el.text
            filtered_page_text = remove_non_printable(page_text)
            total_extracted_text[page_num_str] = filtered_page_text
        elif mode == "entire_page":
            # OCR'ing entire page (new approach to implement)
            text_extraction_start_time = time.time()

            ocr_data = pytesseract.image_to_data(image, lang="eng", output_type=Output.DICT)
            boxes = ocr_data["level"]
            extracted_text_list = []
            for k in range(len(boxes)):
                (x, y, w, h) = (
                    ocr_data["left"][k],
                    ocr_data["top"][k],
                    ocr_data["width"][k],
                    ocr_data["height"][k],
                )
                extracted_text = ocr_data["text"][k]
                if not extracted_text:
                    continue

                extracted_region = Rectangle(x1=x, y1=y, x2=x + w, y2=y + h)

                extracted_is_subregion_of_inferred = False
                for inferred_region in inferred_layout:
                    extracted_is_subregion_of_inferred = extracted_region.is_almost_subregion_of(
                        inferred_region.pad(12),
                        subregion_threshold=0.75,
                    )
                    if extracted_is_subregion_of_inferred:
                        break

                if extracted_is_subregion_of_inferred:
                    extracted_text_list.append(extracted_text)

                if drawable:
                    if extracted_is_subregion_of_inferred:
                        cv2.rectangle(cv_img, (x, y), (x + w, y + h), (0, 255, 0), 2, None)
                    else:
                        cv2.rectangle(cv_img, (x, y), (x + w, y + h), (255, 0, 0), 2, None)

            text_extraction_infer_time = time.time() - text_extraction_start_time
            total_text_extraction_infer_time += text_extraction_infer_time

            page_text = " ".join(extracted_text_list)
            filtered_page_text = remove_non_printable(page_text)
            total_extracted_text[page_num_str] = filtered_page_text
        else:
            raise ValueError("Invalid mode")

        if drawable:
            for el in inferred_layout:
                pt1 = [int(el.x1), int(el.y1)]
                pt2 = [int(el.x2), int(el.y2)]
                cv2.rectangle(
                    img=cv_img,
                    pt1=pt1,
                    pt2=pt2,
                    color=(0, 0, 255),
                    thickness=4,
                    lineType=None,
                )

            f_path = os.path.join(output_dir, f"ocr_{mode}_{page_num_str}.jpg")
            cv2.imwrite(f_path, cv_img)

        if printable:
            print(
                f"page: {i + 1} - n_layout_elements: {len(inferred_layout)} - "
                f"text_extraction_infer_time: {text_extraction_infer_time}"
            )

    return total_text_extraction_infer_time, total_extracted_text


def run_ocr(
    images,
    printable=True,
):
    total_text_extraction_infer_time = 0
    total_text = ""
    for i, image in enumerate(images):
        text_extraction_start_time = time.time()

        page_text = pytesseract.image_to_string(image)

        text_extraction_infer_time = time.time() - text_extraction_start_time

        if printable:
            print(f"page: {i + 1} - text_extraction_infer_time: {text_extraction_infer_time}")

        total_text_extraction_infer_time += text_extraction_infer_time
        total_text += page_text

    return total_text_extraction_infer_time, total_text
