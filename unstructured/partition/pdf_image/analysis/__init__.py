import json
from pathlib import Path
from typing import Optional

from unstructured import env_config
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


def save_analysis_artifiacts(
    *layout_dumpers: LayoutDumper, filename: str, analyzed_image_output_dir_path: str
):
    """Save the analysis artifacts for a given file. Loads some settings from
    the environment configuration.

    Args:
        layout_dumpers: The layout dumpers to save and use for bboxes rendering
        filename: The filename of the sources analyzed file (pdf/image)
        analyzed_image_output_dir_path: The directory to save the analysis artifacts
    """
    skip_bboxes = env_config.ANALYSIS_BBOX_SKIP
    skip_dump_od = env_config.ANALYSIS_DUMP_OD_SKIP
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
            save_dir=output_path,
            draw_grid=env_config.ANALYSIS_BBOX_DRAW_GRID,
            draw_caption=env_config.ANALYSIS_BBOX_DRAW_CAPTION,
            resize=env_config.ANALYSIS_BBOX_RESIZE,
            format=env_config.ANALYSIS_BBOX_FORMAT,
        )

        for layout_dumper in layout_dumpers:
            drawer = _get_drawer_for_dumper(layout_dumper)
            analysis_drawer.add_drawer(drawer)
        analysis_drawer.process()


def render_bboxes_for_file(
    filename: str,
    analyzed_image_output_dir_path: str,
    renders_output_dir_path: Optional[str] = None,
):
    """Render the bounding boxes for a given layout dimp file.
    Expects that the analyzed_image_output_dir_path keeps the structure
    that was created by the save_analysis_artifacts function.

    Args:
        filename: The filename of the sources analyzed file (pdf/image)
        analyzed_image_output_dir_path: The directory where the analysis artifacts
          (layout dumps) are saved. It should be the root directory of the structure
          created by the save_analysis_artifacts function.
        renders_output_dir_path: Optional directory to save the rendered bboxes -
          if not provided, it will be saved in the analysis directory.
    """
    filename_stem = Path(filename).stem
    analysis_dumps_dir = (
        Path(analyzed_image_output_dir_path) / "analysis" / filename_stem / "layout_dump"
    )
    print(f"analysis_dumps_dir: {analysis_dumps_dir}")
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
            draw_grid=env_config.ANALYSIS_BBOX_DRAW_GRID,
            draw_caption=env_config.ANALYSIS_BBOX_DRAW_CAPTION,
            resize=env_config.ANALYSIS_BBOX_RESIZE,
            format=env_config.ANALYSIS_BBOX_FORMAT,
        )

        for drawer in layout_drawers:
            analysis_drawer.add_drawer(drawer)
        analysis_drawer.process()