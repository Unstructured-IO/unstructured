import json
import os
import time
from datetime import datetime
from difflib import SequenceMatcher

import nltk
import pdf2image

from unstructured_inference.inference.layout import (
    DocumentLayout,
    create_image_output_dir,
    process_file_with_model,
)

# Download the required resources (run this once)
nltk.download("punkt")


def validate_performance(
    f_name,
    validation_mode,
    is_image_file=False,
):
    print(
        f">>> Start performance comparison - filename: {f_name}"
        f" - validation_mode: {validation_mode}"
        f" - is_image_file: {is_image_file}"
    )

    now_dt = datetime.utcnow()
    now_str = now_dt.strftime("%Y_%m_%d-%H_%M_%S")

    f_path = os.path.join(example_docs_dir, f_name)

    image_f_paths = []
    if validation_mode == "pdf":
        pdf_info = pdf2image.pdfinfo_from_path(f_path)
        n_pages = pdf_info["Pages"]
    elif validation_mode == "image":
        if is_image_file:
            image_f_paths.append(f_path)
        else:
            image_output_dir = create_image_output_dir(f_path)
            images = pdf2image.convert_from_path(f_path, output_folder=image_output_dir)
            image_f_paths = [image.filename for image in images]
        n_pages = len(image_f_paths)
    else:
        n_pages = 0

    processing_result = {}
    for ocr_mode in ["individual_blocks", "entire_page"]:
        start_time = time.time()

        if validation_mode == "pdf":
            layout = process_file_with_model(
                f_path,
                model_name=None,
                ocr_mode=ocr_mode,
            )
        elif validation_mode == "image":
            pages = []
            for image_f_path in image_f_paths:
                _layout = process_file_with_model(
                    image_f_path,
                    model_name=None,
                    ocr_mode=ocr_mode,
                    is_image=True,
                )
                pages += _layout.pages
            for i, page in enumerate(pages):
                page.number = i + 1
            layout = DocumentLayout.from_pages(pages)
        else:
            layout = None

        infer_time = time.time() - start_time

        if layout is None:
            print("Layout is None")
            return

        full_text = str(layout)
        page_text = {}
        for page in layout.pages:
            page_text[page.number] = str(page)

        processing_result[ocr_mode] = {
            "infer_time": infer_time,
            "full_text": full_text,
            "page_text": page_text,
        }

    individual_mode_page_text = processing_result["individual_blocks"]["page_text"]
    entire_mode_page_text = processing_result["individual_blocks"]["page_text"]
    individual_mode_full_text = processing_result["individual_blocks"]["full_text"]
    entire_mode_full_text = processing_result["entire_page"]["full_text"]

    compare_result = compare_processed_text(individual_mode_full_text, entire_mode_full_text)

    report = {
        "validation_mode": validation_mode,
        "file_info": {
            "filename": f_name,
            "n_pages": n_pages,
        },
        "processing_time": {
            "individual_blocks": processing_result["individual_blocks"]["infer_time"],
            "entire_page": processing_result["entire_page"]["infer_time"],
        },
        "text_similarity": compare_result,
        "extracted_text": {
            "individual_blocks": {
                "page_text": individual_mode_page_text,
                "full_text": individual_mode_full_text,
            },
            "entire_page": {
                "page_text": entire_mode_page_text,
                "full_text": entire_mode_full_text,
            },
        },
    }

    write_report(report, now_str, validation_mode)

    print("<<< End performance comparison", f_name)


def compare_processed_text(individual_mode_full_text, entire_mode_full_text, delimiter=" "):
    # Calculate similarity ratio
    similarity_ratio = SequenceMatcher(
        None, individual_mode_full_text, entire_mode_full_text
    ).ratio()

    print(f"similarity_ratio: {similarity_ratio}")

    # Tokenize the text into words
    word_list_individual = nltk.word_tokenize(individual_mode_full_text)
    n_word_list_individual = len(word_list_individual)
    print("n_word_list_in_text_individual:", n_word_list_individual)
    word_sets_individual = set(word_list_individual)
    n_word_sets_individual = len(word_sets_individual)
    print(f"n_word_sets_in_text_individual: {n_word_sets_individual}")
    # print("word_sets_merged:", word_sets_merged)

    word_list_entire = nltk.word_tokenize(entire_mode_full_text)
    n_word_list_entire = len(word_list_entire)
    print("n_word_list_individual:", n_word_list_entire)
    word_sets_entire = set(word_list_entire)
    n_word_sets_entire = len(word_sets_entire)
    print(f"n_word_sets_individual: {n_word_sets_entire}")
    # print("word_sets_individual:", word_sets_individual)

    # Find unique elements using difference
    print("diff_elements:")
    unique_words_individual = word_sets_individual - word_sets_entire
    unique_words_entire = word_sets_entire - word_sets_individual
    print(f"unique_words_in_text_individual: {unique_words_individual}\n")
    print(f"unique_words_in_text_entire: {unique_words_entire}")

    return {
        "similarity_ratio": similarity_ratio,
        "individual_blocks": {
            "n_word_list": n_word_list_individual,
            "n_word_sets": n_word_sets_individual,
            "unique_words": delimiter.join(list(unique_words_individual)),
        },
        "entire_page": {
            "n_word_list": n_word_list_entire,
            "n_word_sets": n_word_sets_entire,
            "unique_words": delimiter.join(list(unique_words_entire)),
        },
    }


def write_report(report, now_str, validation_mode):
    report_f_name = f"validate-ocr-{validation_mode}-{now_str}.json"
    report_f_path = os.path.join(output_dir, report_f_name)
    with open(report_f_path, "w", encoding="utf-8-sig") as f:
        json.dump(report, f, indent=4)


def run():
    test_files = [
        {"name": "layout-parser-paper-fast.pdf", "mode": "image", "is_image_file": False},
        {"name": "loremipsum_multipage.pdf", "mode": "image", "is_image_file": False},
        {"name": "2023-Jan-economic-outlook.pdf", "mode": "image", "is_image_file": False},
        {"name": "recalibrating-risk-report.pdf", "mode": "image", "is_image_file": False},
        {"name": "Silent-Giant.pdf", "mode": "image", "is_image_file": False},
    ]

    for test_file in test_files:
        f_name = test_file["name"]
        validation_mode = test_file["mode"]
        is_image_file = test_file["is_image_file"]

        validate_performance(f_name, validation_mode, is_image_file)


if __name__ == "__main__":
    cur_dir = os.getcwd()
    base_dir = os.path.join(cur_dir, os.pardir, os.pardir)
    example_docs_dir = os.path.join(base_dir, "sample-docs")

    # folder path to save temporary outputs
    output_dir = os.path.join(cur_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    run()
