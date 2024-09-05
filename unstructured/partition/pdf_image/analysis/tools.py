import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from unstructured.partition.pdf_image.analysis.bbox_visualisation import (
    AnalysisDrawer,
    FinalLayoutDrawer,
    LayoutDrawer,
    OCRLayoutDrawer,
    ODModelLayoutDrawer,
    PdfminerLayoutDrawer,
)
from unstructured.partition.pdf_image.analysis.layout_dump import (
    ExtractedLayoutDumper,
    FinalLayoutDumper,
    JsonLayoutDumper,
    LayoutDumper,
    ObjectDetectionLayoutDumper,
    OCRLayoutDumper,
)


def _get_drawer_for_dumper(dumper: LayoutDumper) -> Optional[LayoutDrawer]:
    """For a given layout dumper, return the corresponding layout drawer instance initialized with
    a dumped layout dict.

    Args:
        dumper: The layout dumper instance

    Returns:
        LayoutDrawer: The corresponding layout drawer instance
    """
    if isinstance(dumper, ObjectDetectionLayoutDumper):
        return ODModelLayoutDrawer(layout_dump=dumper.dump())
    elif isinstance(dumper, ExtractedLayoutDumper):
        return PdfminerLayoutDrawer(layout_dump=dumper.dump())
    elif isinstance(dumper, OCRLayoutDumper):
        return OCRLayoutDrawer(layout_dump=dumper.dump())
    elif isinstance(dumper, FinalLayoutDumper):
        return FinalLayoutDrawer(layout_dump=dumper.dump())
    else:
        raise ValueError(f"Unknown dumper type: {dumper}")


def _generate_filename(is_image: bool):
    """Generate a filename for the analysis artifacts based on the file type.
    Adds a random uuid suffix
    """
    suffix = uuid.uuid4().hex[:5]
    if is_image:
        return f"image_{suffix}.png"
    return f"pdf_{suffix}.pdf"


def save_analysis_artifiacts(
    *layout_dumpers: LayoutDumper,
    is_image: bool,
    analyzed_image_output_dir_path: str,
    filename: Optional[str] = None,
    file: Optional[BytesIO] = None,
    skip_bboxes: bool = False,
    skip_dump_od: bool = False,
    draw_grid: bool = False,
    draw_caption: bool = True,
    resize: Optional[float] = None,
    format: str = "png",
):
    """Save the analysis artifacts for a given file. Loads some settings from
    the environment configuration.

    Args:
        layout_dumpers: The layout dumpers to save and use for bboxes rendering
        is_image: Flag for the file type (pdf/image)
        analyzed_image_output_dir_path: The directory to save the analysis artifacts
        filename: The filename of the sources analyzed file (pdf/image).
            Only one of filename or file should be provided.
        file: The file object for the analyzed file.
            Only one of filename or file should be provided.
        draw_grid: Flag for drawing the analysis bboxes on a single image (as grid)
        draw_caption: Flag for drawing the caption above the analyzed page (for e.g. layout source)
        resize: Output image resize value. If not provided, the image will not be resized.
        format: The format for analyzed pages with bboxes drawn on them. Default is 'png'.
    """
    if not filename:
        filename = _generate_filename(is_image)
    if skip_bboxes or skip_dump_od:
        return

    output_path = Path(analyzed_image_output_dir_path)
    output_path.mkdir(parents=True, exist_ok=True)
    if not skip_dump_od:
        json_layout_dumper = JsonLayoutDumper(
            filename=filename,
            save_dir=output_path,
        )
        for layout_dumper in layout_dumpers:
            json_layout_dumper.add_layout_dumper(layout_dumper)
        json_layout_dumper.process()

    if not skip_bboxes:
        analysis_drawer = AnalysisDrawer(
            filename=filename,
            file=file,
            is_image=is_image,
            save_dir=output_path,
            draw_grid=draw_grid,
            draw_caption=draw_caption,
            resize=resize,
            format=format,
        )

        for layout_dumper in layout_dumpers:
            drawer = _get_drawer_for_dumper(layout_dumper)
            analysis_drawer.add_drawer(drawer)
        analysis_drawer.process()


def render_bboxes_for_file(
    filename: str,
    analyzed_image_output_dir_path: str,
    renders_output_dir_path: Optional[str] = None,
    draw_grid: bool = False,
    draw_caption: bool = True,
    resize: Optional[float] = None,
    format: str = "png",
):
    """Render the bounding boxes for a given layout dimp file.
    To be used for analysis after the partition is performed for
    only dumping the layouts - the bboxes can be rendered later.

    Expects that the analyzed_image_output_dir_path keeps the structure
    that was created by the save_analysis_artifacts function.

    Args:
        filename: The filename of the sources analyzed file (pdf/image)
        analyzed_image_output_dir_path: The directory where the analysis artifacts
          (layout dumps) are saved. It should be the root directory of the structure
          created by the save_analysis_artifacts function.
        renders_output_dir_path: Optional directory to save the rendered bboxes -
          if not provided, it will be saved in the analysis directory.
        draw_grid: Flag for drawing the analysis bboxes on a single image (as grid)
        draw_caption: Flag for drawing the caption above the analyzed page (for e.g. layout source)
        resize: Output image resize value. If not provided, the image will not be resized.
        format: The format for analyzed pages with bboxes drawn on them. Default is 'png'.
    """
    filename_stem = Path(filename).stem
    is_image = not Path(filename).suffix.endswith("pdf")
    analysis_dumps_dir = (
        Path(analyzed_image_output_dir_path) / "analysis" / filename_stem / "layout_dump"
    )
    if not analysis_dumps_dir.exists():
        return
    layout_drawers = []
    for analysis_dump_filename in analysis_dumps_dir.iterdir():
        if not analysis_dump_filename.is_file():
            continue
        with open(analysis_dump_filename) as f:
            layout_dump = json.load(f)
        if analysis_dump_filename.stem == "final":
            layout_drawers.append(FinalLayoutDrawer(layout_dump=layout_dump))
        if analysis_dump_filename.stem == "object_detection":
            layout_drawers.append(ODModelLayoutDrawer(layout_dump=layout_dump))
        if analysis_dump_filename.stem == "ocr":
            layout_drawers.append(OCRLayoutDrawer(layout_dump=layout_dump))
        if analysis_dump_filename.stem == "pdfminer":
            layout_drawers.append(PdfminerLayoutDrawer(layout_dump=layout_dump))

    if layout_drawers:
        if not renders_output_dir_path:
            output_path = (
                Path(analyzed_image_output_dir_path) / "analysis" / filename_stem / "bboxes"
            )
        else:
            output_path = Path(renders_output_dir_path)
        output_path.mkdir(parents=True, exist_ok=True)
        analysis_drawer = AnalysisDrawer(
            filename=filename,
            save_dir=output_path,
            is_image=is_image,
            draw_grid=draw_grid,
            draw_caption=draw_caption,
            resize=resize,
            format=format,
        )

        for drawer in layout_drawers:
            analysis_drawer.add_drawer(drawer)
        analysis_drawer.process()
