import argparse
import logging
import os
from pathlib import Path

from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import elements_from_json, elements_to_md

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def json_to_format(
    filepath: Path,
    outdir: Path,
    format_type: str,
    exclude_binary_image_data: bool,
    no_group_by_page: bool,
):
    logger.info("Processing: %s", filepath)
    elements = elements_from_json(str(filepath))

    if format_type == "html":
        output_content = elements_to_html(elements, exclude_binary_image_data, no_group_by_page)
        file_extension = ".html"
    elif format_type == "markdown":
        output_content = elements_to_md(
            elements, exclude_binary_image_data=exclude_binary_image_data
        )
        file_extension = ".md"
    else:
        raise ValueError(f"Unsupported format: {format_type}. Supported formats: html, markdown")

    outpath = outdir / filepath.with_suffix(file_extension).name
    os.makedirs(outpath.parent, exist_ok=True)
    with open(outpath, "w+") as f:
        f.write(output_content)
    logger.info(f"{format_type.upper()} rendered and saved to: %s", outpath)


def multiple_json_to_format(
    path: Path,
    outdir: Path,
    format_type: str,
    exclude_binary_image_data: bool,
    no_group_by_page: bool,
):
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                json_file_path = Path(root) / file
                outpath = outdir / json_file_path.relative_to(path).parent
                json_to_format(
                    json_file_path,
                    outpath,
                    format_type,
                    exclude_binary_image_data,
                    no_group_by_page,
                )


def main():
    parser = argparse.ArgumentParser(description="Convert JSON elements to HTML or Markdown.")
    parser.add_argument(
        "filepath",
        type=str,
        help="""Path to the JSON file or directory containing elements.
        If given directory it will convert all JSON files in directory
        and all sub-directories.""",
    )
    parser.add_argument(
        "--outdir", type=str, help="Output directory for the output file.", default=""
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["html", "markdown"],
        default="html",
        help="Output format: html or markdown (default: html)",
    )
    parser.add_argument(
        "--exclude-img", action="store_true", help="Exclude binary image data from the output."
    )
    parser.add_argument(
        "--no-group", action="store_true", help="Don't group elements by pages (HTML only)."
    )
    args = parser.parse_args()

    filepath = Path(args.filepath)
    outdir = Path(args.outdir)

    if filepath.is_file():
        json_to_format(filepath, outdir, args.format, args.exclude_img, args.no_group)
    else:
        multiple_json_to_format(filepath, outdir, args.format, args.exclude_img, args.no_group)


if __name__ == "__main__":
    main()
