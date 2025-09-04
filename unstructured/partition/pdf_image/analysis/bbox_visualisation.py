import logging
import math
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Generator, List, Optional, TypeVar, Union

import numpy as np
from matplotlib import colors, font_manager
from PIL import Image, ImageDraw, ImageFont
from unstructured_inference.constants import ElementType

from unstructured.partition.pdf_image.analysis.processor import AnalysisProcessor
from unstructured.partition.pdf_image.pdf_image_utils import convert_pdf_to_image

PageImage = TypeVar("PageImage", Image.Image, np.ndarray)


def get_font():
    preferred_fonts = ["Arial.ttf"]
    available_fonts = font_manager.findSystemFonts()
    if not available_fonts:
        raise ValueError("No fonts available")
    for font in preferred_fonts:
        for available_font in available_fonts:
            if font in available_font:
                return available_font
    return available_fonts[0]


COLOR_WHITE = ("white", (255, 255, 255))
COLOR_BLACK = ("black", (0, 0, 0))


class TextAlignment(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"


@dataclass
class BboxLabels:
    top_left: Optional[str] = None
    top_right: Optional[str] = None
    bottom_left: Optional[str] = None
    bottom_right: Optional[str] = None
    center: Optional[str] = None


@dataclass
class BBox:
    points: tuple[int, int, int, int]
    labels: Optional[BboxLabels] = None


def get_rgb_color(color: str) -> tuple[int, int, int]:
    """Convert a color name to RGB values.

    Args:
        color: A color name supported by matplotlib.

    Returns:
        A tuple of three integers representing the RGB values of the color.
    """
    try:
        rgb_colors = colors.to_rgb(color)
    except ValueError:
        print("Error")
        raise
    return int(rgb_colors[0] * 255), int(rgb_colors[1] * 255), int(rgb_colors[2] * 255)


def _get_bbox_to_page_ratio(bbox: tuple[int, int, int, int], page_size: tuple[int, int]) -> float:
    """Compute the ratio of the bounding box to the page size.

    Args:
        bbox: Tuple containing coordinates of the bbox: (x1, y1, x2, y2).
        page_size: Tuple containing page size: (width, height).

    Returns:
        The ratio of the bounding box to the page size.
    """
    x1, y1, x2, y2 = bbox
    page_width, page_height = page_size
    page_diagonal = math.sqrt(page_height**2 + page_width**2)
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    bbox_diagonal = math.sqrt(bbox_height**2 + bbox_width**2)
    return bbox_diagonal / page_diagonal


def _get_optimal_value_for_bbox(
    bbox: tuple[int, int, int, int],
    page_size: tuple[int, int],
    min_value: int,
    max_value: int,
    ratio_for_min_value: float = 0.01,
    ratio_for_max_value: float = 0.5,
) -> int:
    """Compute the optimal value for a given bounding box using a linear function
    generated for given min and max values and ratios

    Args:
        bbox: Tuple containing coordinates of the bbox: (x1, y1, x2, y2).
        page_size: Tuple containing page size: (width, height).
        min_value: The minimum value returned by the function.
        max_value: The maximum value returned by the function.
        ratio_for_min_value: The ratio of the bbox to page size for the min value.
        ratio_for_max_value: The ratio of the bbox to page size for the max value.

    Returns:
        The optimal value for the given bounding box and parameters given.
    """
    bbox_to_page_ratio = _get_bbox_to_page_ratio(bbox, page_size)
    coefficients = np.polyfit((ratio_for_min_value, ratio_for_max_value), (min_value, max_value), 1)
    value = int(bbox_to_page_ratio * coefficients[0] + coefficients[1])
    return max(min_value, min(max_value, value))


def get_bbox_text_size(
    bbox: tuple[int, int, int, int],
    page_size: tuple[int, int],
    min_font_size: int = 16,
    max_font_size: int = 32,
) -> int:
    """Compute the optimal font size for a given bounding box.

    Args:
        bbox: Tuple containing coordinates of the bbox: (x1, y1, x2, y2).
        page_size: Tuple containing page size: (width, height).
        min_font_size: The minimum font size returned by the function.
        max_font_size: The maximum font size returned by the function.

    Returns:
        The optimal font size for the given bounding box.
    """
    return _get_optimal_value_for_bbox(
        bbox=bbox,
        page_size=page_size,
        min_value=min_font_size,
        max_value=max_font_size,
    )


def get_bbox_thickness(
    bbox: tuple[int, int, int, int],
    page_size: tuple[int, int],
    min_thickness: int = 1,
    max_thickness: int = 4,
) -> float:
    """Compute the optimal thickness for a given bounding box.

    Args:
        bbox: Tuple containing coordinates of the bbox: (x1, y1, x2, y2).
        page_size: Tuple containing page size: (width, height).
        min_thickness: The minimum font size returned by the function.
        max_thickness: The maximum font size returned by the function.

    Returns:

    """
    return _get_optimal_value_for_bbox(
        bbox=bbox,
        page_size=page_size,
        min_value=min_thickness,
        max_value=max_thickness,
    )


def get_text_color(
    background_color: Union[str, tuple[int, int, int]], brightness_threshold: float = 0.5
) -> tuple[str, tuple[int, int, int]]:
    """Returns the contrastive text color (black or white) for a given background color.

    Args:
        background_color: Tuple containing RGB values of the background color.

    Returns:
        Tuple containing RGB values of the text color.
    """
    if isinstance(background_color, str):
        background_color = get_rgb_color(background_color)
    background_brightness = (
        0.299 * background_color[0] + 0.587 * background_color[1] + 0.114 * background_color[0]
    ) / 255
    if background_brightness > brightness_threshold:
        return COLOR_BLACK
    else:
        return COLOR_WHITE


def get_label_rect_and_coords(
    alignment: TextAlignment,
    bbox_points: tuple[int, int, int, int],
    text_width: int,
    text_height: int,
):
    indent = max(int(text_width * 0.2), 10)
    vertical_correction = max(int(text_height * 0.3), 10)

    # with this the text should be centered in the rectangle
    rect_width = text_width + indent * 2
    # we apply a correction to the height to make the text not overlap over the rectangle
    # (the text height getter looks to return too small value)
    rect_height = text_height + vertical_correction
    x1, y1, x2, y2 = bbox_points
    if alignment is TextAlignment.CENTER:
        # center:
        horizontal_half = int(rect_width / 2 * 1.05)
        vertical_half = int(rect_height / 2 * 1.05)
        center_point = x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2
        # resize rectangle to make it look better in the center
        label_rectangle = (
            (
                center_point[0] - horizontal_half,
                center_point[1] - vertical_half,
            ),
            (
                center_point[0] + horizontal_half,
                center_point[1] + vertical_half,
            ),
        )
        label_coords = (
            center_point[0] - horizontal_half + int(indent * 1.05),
            center_point[1] - vertical_half * 1.05,
        )
    elif alignment is TextAlignment.TOP_LEFT:
        label_rectangle = (
            (x1, y1 - rect_height),
            (x1 + rect_width, y1),
        )
        label_coords = (x1 + indent, y1 - rect_height)
    elif alignment is TextAlignment.TOP_RIGHT:
        label_rectangle = (
            (x2 - rect_width, y1),
            (x2, y1 + rect_height),
        )
        label_coords = (x2 - text_width - indent, y1)
    elif alignment is TextAlignment.BOTTOM_LEFT:
        label_rectangle = (
            (x1, y2 - rect_height),
            (x1 + rect_width, y2),
        )
        label_coords = (x1 + indent, y2 - rect_height)
    elif alignment is TextAlignment.BOTTOM_RIGHT:
        label_rectangle = (
            (x2 - rect_width, y2 - rect_height),
            (x2, y2),
        )
        label_coords = (x2 - text_width - indent, y2 - rect_height)
    else:
        raise ValueError(f"Unknown alignment {alignment}")
    return label_rectangle, label_coords


def draw_bbox_label(
    image_draw: ImageDraw.ImageDraw,
    text: str,
    bbox_points: tuple[int, int, int, int],
    alignment: TextAlignment,
    font_size: int,
    background_color: str,
):
    """Draw a label stick to a bounding box.
    The alignment parameter specifies where the label should be placed.

    Args:
        image_draw:         ImageDraw object to draw on the image.
        text:               Text to draw.
        bbox_points:        Bounding box points.
        alignment:          Text alignment.
        font_size:          Font size of the text.
        background_color:   RGB values of the background color.
    """
    font = ImageFont.truetype(get_font(), font_size)
    text_x1, text_y1, text_x2, text_y2 = image_draw.textbbox(
        (0, 0), text, font=font, align="center"
    )
    text_width = text_x2 - text_x1
    text_height = text_y2 - text_y1

    label_rectangle, label_coords = get_label_rect_and_coords(
        alignment, bbox_points, text_width, text_height
    )

    rgb_background_color = get_rgb_color(background_color)
    try:
        image_draw.rectangle(
            label_rectangle,
            fill=background_color,
            outline=background_color,
        )
    except TypeError:
        image_draw.rectangle(
            label_rectangle,
            fill=rgb_background_color,
            outline=rgb_background_color,
        )
    text_color, text_color_rgb = get_text_color(background_color)
    try:
        image_draw.text(label_coords, text, fill=text_color, font=font, align="center")
    except TypeError:
        image_draw.text(label_coords, text, fill=text_color_rgb, font=font, align="center")


def draw_bbox_on_image(
    image_draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color: str,
):
    """Draw bbox with additional labels on the image..

    Args:
        image_draw:     ImageDraw object to draw on the image.
        bbox:           Bounding box to draw.
        color:          RGB values of the color of the bounding box (edges + label backgrounds).
    """
    x1, y1, x2, y2 = bbox.points
    if x1 >= x2 or y1 >= y2:
        print(f"Invalid bbox coordinates: {bbox.points}")
        return
    top_left = x1, y1  # the main
    bottom_right = x2, y2
    box_thickness = get_bbox_thickness(bbox=bbox.points, page_size=image_draw.im.size)
    font_size = get_bbox_text_size(bbox=bbox.points, page_size=image_draw.im.size)

    try:
        image_draw.rectangle((top_left, bottom_right), outline=color, width=box_thickness)
    except TypeError:
        rgb_color = get_rgb_color(color)
        image_draw.rectangle((top_left, bottom_right), outline=rgb_color, width=box_thickness)

    if bbox.labels is not None:
        if top_left_label := bbox.labels.top_left:
            draw_bbox_label(
                image_draw,
                top_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if top_right_label := bbox.labels.top_right:
            draw_bbox_label(
                image_draw,
                top_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_left_label := bbox.labels.bottom_left:
            draw_bbox_label(
                image_draw,
                bottom_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_right_label := bbox.labels.bottom_right:
            draw_bbox_label(
                image_draw,
                bottom_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if center_label := bbox.labels.center:
            draw_bbox_label(
                image_draw,
                center_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.CENTER,
                font_size=font_size * 2,
                background_color=color,
            )


class LayoutDrawer(ABC):
    layout_source: str = "unknown"
    laytout_dump: dict

    def __init__(self, layout_dump: dict):
        self.layout_dump = layout_dump

    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
        """Draw the layout bboxes with additional metadata on the image."""
        layout_pages = self.layout_dump.get("pages")
        if not layout_pages:
            print(f"Warning: layout in drawer {self.__class__.__name__} is empty - skipping")
            return page_image
        if len(layout_pages) < page_num:
            print(f"Error! Page {page_num} not found in layout (pages: {len(layout_pages)})")
            return page_image
        image_draw = ImageDraw.ImageDraw(page_image)
        page_layout_dump = layout_pages[page_num - 1]
        if page_num != page_layout_dump.get("number"):
            dump_page_num = page_layout_dump.get("number")
            print(f"Warning: Requested page num {page_num} differs from dump {dump_page_num}")
        for idx, elements in enumerate(page_layout_dump["elements"], 1):
            self.render_element_on_page(idx, image_draw, elements)
        return page_image

    @abstractmethod
    def render_element_on_page(self, idx: int, image_draw: ImageDraw, elements: dict[str, Any]):
        """Draw a single element on the image."""


class SimpleLayoutDrawer(LayoutDrawer, ABC):
    color: str
    show_order: bool = False
    show_text_length: bool = False

    def render_element_on_page(self, idx: int, image_draw: ImageDraw, elements: dict[str, Any]):
        text_len = len(elements["text"]) if elements.get("text") else 0
        element_prob = elements.get("prob")
        element_order = f"{idx}" if self.show_order else None
        text_len = f"len: {text_len}" if self.show_text_length else None
        bbox = BBox(
            points=elements["bbox"],
            labels=BboxLabels(
                top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                bottom_left=text_len,
                center=element_order,
            ),
        )
        draw_bbox_on_image(image_draw, bbox, color=self.color)


class PdfminerLayoutDrawer(SimpleLayoutDrawer):
    layout_source = "pdfminer"

    def __init__(self, layout_dump: dict, color: str = "red"):
        self.layout_dump = layout_dump
        self.color = color
        self.show_order = True
        super().__init__(layout_dump)


class OCRLayoutDrawer(SimpleLayoutDrawer):
    layout_source = "ocr"

    def __init__(self, layout_dump: dict, color: str = "red"):
        self.color = color
        self.show_order = False
        self.show_text_length = False
        super().__init__(layout_dump)


class ODModelLayoutDrawer(LayoutDrawer):
    layout_source = "od_model"

    color_map = {
        ElementType.CAPTION: "salmon",
        ElementType.FOOTNOTE: "orange",
        ElementType.FORMULA: "mediumpurple",
        ElementType.LIST_ITEM: "navy",
        ElementType.PAGE_FOOTER: "deeppink",
        ElementType.PAGE_HEADER: "green",
        ElementType.PICTURE: "sienna",
        ElementType.SECTION_HEADER: "darkorange",
        ElementType.TABLE: "blue",
        ElementType.TEXT: "turquoise",
        ElementType.TITLE: "greenyellow",
    }

    def render_element_on_page(self, idx: int, image_draw: ImageDraw, elements: dict[str, Any]):
        element_type = elements["type"]
        element_prob = elements.get("prob")
        bbox_points = elements["bbox"]
        color = self.get_element_type_color(element_type)
        bbox = BBox(
            points=bbox_points,
            labels=BboxLabels(
                top_left=f"{element_type}",
                top_right=f"prob: {element_prob:.2f}" if element_prob else None,
            ),
        )
        draw_bbox_on_image(image_draw, bbox, color=color)

    def get_element_type_color(self, element_type: str) -> str:
        return self.color_map.get(element_type, "cyan")


class FinalLayoutDrawer(LayoutDrawer):
    layout_source = "final"

    color_map = {
        "CheckBox": "brown",
        "ListItem": "red",
        "Title": "greenyellow",
        "NarrativeText": "turquoise",
        "Header": "green",
        "Footer": "orange",
        "FigureCaption" "Image": "sienna",
        "Table": "blue",
        "Address": "gold",
        "EmailAddress": "lightskyblue",
        "Formula": "mediumpurple",
        "CodeSnippet": "magenta",
        "PageNumber": "crimson",
    }

    def __init__(self, layout_dump: dict):
        self.layout_dump = layout_dump

    def render_element_on_page(self, idx: int, image_draw: ImageDraw, elements: dict[str, Any]):
        element_type = elements["type"]
        element_prob = elements.get("prob")
        text_len = len(elements["text"]) if elements.get("text") else 0
        bbox_points = elements["bbox"]
        color = self.get_element_type_color(element_type)
        cluster = elements.get("cluster")
        bbox = BBox(
            points=bbox_points,
            labels=BboxLabels(
                top_left=f"{element_type}",
                top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                bottom_right=f"len: {text_len}",
                bottom_left=f"cl: {cluster}" if cluster else None,
                center=f"{idx}",
            ),
        )
        draw_bbox_on_image(image_draw, bbox, color=color)

    def get_element_type_color(self, element_type: str) -> str:
        return self.color_map.get(element_type, "cyan")


class AnalysisDrawer(AnalysisProcessor):
    def __init__(
        self,
        filename: Optional[Union[str, Path]],
        is_image: bool,
        save_dir: Union[str, Path],
        file: Optional[BytesIO] = None,
        draw_caption: bool = True,
        draw_grid: bool = False,
        resize: Optional[float] = None,
        format: str = "png",
    ):
        self.draw_caption = draw_caption
        self.draw_grid = draw_grid
        self.resize = resize
        self.is_image = is_image
        self.format = format
        self.drawers = []
        self.file = file

        super().__init__(filename, save_dir)

    def add_drawer(self, drawer: LayoutDrawer):
        self.drawers.append(drawer)

    def process(self):
        filename_stem = Path(self.filename).stem
        analysis_save_dir = Path(self.save_dir) / "analysis" / filename_stem / "bboxes"
        analysis_save_dir.mkdir(parents=True, exist_ok=True)

        for page_idx, orig_image_page in enumerate(self.load_source_image()):
            images_for_grid = []
            page_num = page_idx + 1
            for drawer in self.drawers:
                try:
                    image = drawer.draw_layout_on_page(orig_image_page.copy(), page_num=page_num)
                except:  # noqa: E722
                    logging.exception(
                        f"Error while drawing layout for page {page_num} "
                        f"for file {self.filename} with drawer "
                        f"{drawer.__class__.__name__}"
                    )
                    continue
                if self.draw_caption:
                    image = self.add_caption(
                        image, caption=f"Layout source: {drawer.layout_source}"
                    )
                if not self.draw_grid:
                    if self.resize is not None:
                        image = image.resize(
                            (int(image.width * self.resize), int(image.height * self.resize)),
                        )
                    image.save(
                        analysis_save_dir / f"page{page_num}"
                        f"_layout_{drawer.layout_source}.{self.format}",
                        optimize=True,
                        quality=85,
                    )
                    image.close()
                else:
                    images_for_grid.append(image)
            if images_for_grid:
                grid_image = self.paste_images_on_grid(images_for_grid)
                if self.resize is not None:
                    grid_image = grid_image.resize(
                        (int(grid_image.width * self.resize), int(grid_image.height * self.resize))
                    )
                grid_image.save(
                    analysis_save_dir / f"page{page_num}_layout_all.{self.format}",
                    optimize=True,
                    quality=85,
                )
                grid_image.close()

    def add_caption(self, image: Image.Image, caption: str):
        font = ImageFont.truetype(get_font(), 52)
        draw = ImageDraw.ImageDraw(image)
        text_x1, text_y1, text_x2, text_y2 = draw.textbbox(
            (0, 0), caption, font=font, align="center"
        )
        text_width = text_x2 - text_x1
        text_height = int((text_y2 - text_y1) * 1.5)
        text_xy = (image.width - text_width) // 2, 10
        caption_image = Image.new("RGB", (image.width, text_height), color=(255, 255, 255))
        caption_draw = ImageDraw.ImageDraw(caption_image)
        caption_draw.text(text_xy, caption, (0, 0, 0), font=font)

        expanded_image = Image.new("RGB", (image.width, image.height + text_height))
        expanded_image.paste(caption_image, (0, 0))
        expanded_image.paste(image, (0, text_height))
        image.close()
        return expanded_image

    def paste_images_on_grid(self, images: List[Image.Image]) -> Image.Image:
        """Creates a single image that presents all the images on a grid 2 x n/2"""

        pairs = []
        for i in range(0, len(images), 2):
            left_image = images[i]
            right_image = images[i + 1] if i < len(images) - 1 else None
            pairs.append((left_image, right_image))

        max_pair_width = max([pair[0].width + (pair[1].width if pair[1] else 0) for pair in pairs])
        sum_height = sum([max(pair[0].height, pair[1].height if pair[1] else 0) for pair in pairs])

        new_im = Image.new("RGB", (max_pair_width, sum_height))

        height_shift = 0
        for image_left, image_right in pairs:
            new_im.paste(image_left, (0, height_shift))
            if image_right:
                new_im.paste(image_right, (image_left.width, height_shift))
            height_shift += max(image_left.height, image_right.height if image_right else 0)

        for image in images:
            image.close()
        return new_im

    def load_source_image(self) -> Generator[Image.Image, None, None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = []
            if self.is_image:
                if self.file:
                    try:
                        image = Image.open(self.file)
                        output_file = Path(temp_dir) / self.filename
                        image.save(output_file, format="PNG")
                        image_paths = [output_file]
                    except Exception as ex:  # noqa: E722
                        print(
                            f"Error while converting image to PNG for file {self.filename}, "
                            f"exception: {ex}"
                        )
                else:
                    image_paths = [self.filename]
            else:
                try:
                    image_paths = convert_pdf_to_image(
                        filename=self.filename,
                        file=self.file,
                        output_folder=temp_dir,
                        path_only=True,
                    )
                except Exception as ex:  # noqa: E722
                    print(
                        f"Error while converting pdf to image for file {self.filename}",
                        f"exception: {ex}",
                    )

            for image_path in image_paths:
                with Image.open(image_path) as image:
                    yield image.convert("RGB")
