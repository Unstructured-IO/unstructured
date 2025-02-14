import argparse
import logging
import os
from pathlib import Path

from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import elements_from_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def json_to_html(
    filepath: Path, outdir: Path, exclude_binary_image_data: bool, no_group_by_page: bool
):
    logger.info("Processing: %s", filepath)
    elements = elements_from_json(str(filepath))
    elements_html = elements_to_html(elements, exclude_binary_image_data, no_group_by_page)

    outpath = outdir / filepath.with_suffix(".html").name
    os.makedirs(outpath.parent, exist_ok=True)
    with open(outpath, "w+") as f:
        f.write(elements_html)
    logger.info("HTML rendered and saved to: %s", outpath)


def multiple_json_to_html(
    path: Path, outdir: Path, exclude_binary_image_data: bool, no_group_by_page: bool
):
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                json_file_path = Path(root) / file
                outpath = outdir / json_file_path.relative_to(path).parent
                json_to_html(json_file_path, outpath, exclude_binary_image_data, no_group_by_page)


def main():
    parser = argparse.ArgumentParser(description="Convert JSON elements to HTML.")
    parser.add_argument(
        "filepath",
        type=str,
        help="""Path to the JSON file or directory containing elements.
        If given directory it will convert all JSON files in directory
        and all sub-directories.""",
    )
    parser.add_argument(
        "--outdir", type=str, help="Output directory for the HTML file.", default=""
    )
    parser.add_argument(
        "--exclude-img", action="store_true", help="Exclude binary image data from the HTML."
    )
    parser.add_argument("--no-group", action="store_true", help="Don't group elements by pages.")
    args = parser.parse_args()

    filepath = Path(args.filepath)
    outdir = Path(args.outdir)

    if filepath.is_file():
        json_to_html(filepath, outdir, args.exclude_img, args.no_group)
    else:
        multiple_json_to_html(filepath, outdir, args.exclude_img, args.no_group)


if __name__ == "__main__":
    main()
