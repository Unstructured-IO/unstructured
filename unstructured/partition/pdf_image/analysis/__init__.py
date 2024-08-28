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


def _get_drawer_for_dumper(dumper: LayoutDumper) -> LayoutDrawer | None:
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
