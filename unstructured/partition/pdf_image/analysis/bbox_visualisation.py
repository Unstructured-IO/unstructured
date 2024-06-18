import copy
import math
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Collection, Generator, List, Optional, TypeVar, Union

import numpy as np
from matplotlib import colors, font_manager
from PIL import Image, ImageDraw, ImageFont, ImageOps
from unstructured_inference.constants import ElementType
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.inference.layoutelement import LayoutElement

from unstructured.documents.elements import Element, Text
from unstructured.partition.pdf_image.analysis.processor import AnalysisProcessor
from unstructured.partition.pdf_image.pdf_image_utils import convert_pdf_to_image
from unstructured.partition.utils.sorting import coordinates_to_bbox

PageImage = TypeVar("PageImage", Image.Image, np.ndarray)


def get_font():
    preferred_fonts = ["Arial.ttf"]
    available_fonts = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    for font in preferred_fonts:
        for available_font in available_fonts:
            if font in available_font:
                return available_font
    return available_fonts[0]


FONT = get_font()


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
    rgb_colors = colors.to_rgb(color)
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
    background_color: tuple[int, int, int], brightness_threshold: float = 0.5
) -> tuple[int, int, int]:
    """Returns the contrastive text color (black or white) for a given background color.

    Args:
        background_color: Tuple containing RGB values of the background color.

    Returns:
        Tuple containing RGB values of the text color.
    """
    background_brightness = (
        0.299 * background_color[0] + 0.587 * background_color[1] + 0.114 * background_color[0]
    ) / 255
    if background_brightness > brightness_threshold:
        return (0, 0, 0)
    else:
        return (255, 255, 255)


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
    image: Image.Image,
    text: str,
    bbox_points: tuple[int, int, int, int],
    alignment: TextAlignment,
    font_size: int,
    background_color: tuple[int, int, int],
) -> Image.Image:
    """Draw a label stick to a bounding box.
    The alignment parameter specifies where the label should be placed.

    Args:
        image:              Image on which to draw the text box.
        text:               Text to draw.
        bbox_points:        Bounding box points.
        alignment:          Text alignment.
        font_size:          Font size of the text.
        background_color:   RGB values of the background color.

    Returns:
        The image with the text box drawn.
    """
    font = ImageFont.truetype(FONT, font_size)
    draw = ImageDraw.ImageDraw(image)
    text_x1, text_y1, text_x2, text_y2 = draw.textbbox((0, 0), text, font=font, align="center")
    text_width = text_x2 - text_x1
    text_height = text_y2 - text_y1

    label_rectangle, label_coords = get_label_rect_and_coords(
        alignment, bbox_points, text_width, text_height
    )

    draw.rectangle(
        label_rectangle,
        fill=background_color,
        outline=background_color,
    )
    draw.text(label_coords, text, fill=get_text_color(background_color), font=font, align="center")

    return image


def draw_bbox_on_image(image: Image.Image, bbox: BBox, color: tuple[int, int, int]) -> Image.Image:
    """Draw bbox with additional labels on the image..

    Args:
        image:          PIL Image on which to draw the bounding box.
        bbox:           Bounding box to draw.
        color:          RGB values of the color of the bounding box (edges + label backgrounds).

    Returns:
        The image with the bounding box drawn.
    """
    x1, y1, x2, y2 = bbox.points
    top_left = x1, y1  # the main
    bottom_right = x2, y2
    box_thickness = get_bbox_thickness(bbox=bbox.points, page_size=image.size)
    font_size = get_bbox_text_size(bbox=bbox.points, page_size=image.size)

    draw = ImageDraw.ImageDraw(image)
    draw.rectangle((top_left, bottom_right), outline=color, width=box_thickness)

    if bbox.labels is not None:
        if top_left_label := bbox.labels.top_left:
            draw_bbox_label(
                image,
                top_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if top_right_label := bbox.labels.top_right:
            draw_bbox_label(
                image,
                top_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_left_label := bbox.labels.bottom_left:
            draw_bbox_label(
                image,
                bottom_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_right_label := bbox.labels.bottom_right:
            draw_bbox_label(
                image,
                bottom_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if center_label := bbox.labels.center:
            draw_bbox_label(
                image,
                center_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.CENTER,
                font_size=font_size * 2,
                background_color=color,
            )
    return image


class LayoutDrawer(ABC):
    layout_source: str = "unknown"

    @abstractmethod
    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
        """Draw the layout bboxes with additional metadata on the image."""


class SimpleLayoutDrawer(LayoutDrawer, ABC):
    layout: list[list[TextRegion]]
    color: tuple[int, int, int]
    show_order: bool = False
    show_text_length: bool = False

    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
        if not self.layout:
            print(f"Warning: layout in drawer {self.__class__.__name__} is empty - skipping")
            return page_image
        if len(self.layout) < page_num:
            print(f"Error! Page {page_num} not found in layout (pages: {len(self.layout)})")
            return page_image
        page_layout = self.layout[page_num - 1]
        for idx, region in enumerate(page_layout):
            text_len = len(region.text) if region.text else 0
            element_prob = getattr(region, "prob", None)
            element_order = f"{idx + 1}" if self.show_order else None
            text_len = f"len: {text_len}" if self.show_text_length else None
            bbox = BBox(
                points=(region.bbox.x1, region.bbox.y1, region.bbox.x2, region.bbox.y2),
                labels=BboxLabels(
                    top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                    bottom_left=text_len,
                    center=element_order,
                ),
            )
            draw_bbox_on_image(page_image, bbox, color=self.color)
        return page_image


class PdfminerLayoutDrawer(SimpleLayoutDrawer):
    layout_source = "pdfminer"

    def __init__(self, layout: List[List[TextRegion]], color: tuple[int, int, int] = (255, 0, 0)):
        self.layout = copy.deepcopy(layout)
        self.color = color
        self.show_order = True


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

    def __init__(self, layout: DocumentLayout):
        self.layout: list[Collection[LayoutElement]] = copy.deepcopy(
            [page.elements for page in layout.pages]
        )

    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
        if not self.layout:
            print(f"Warning: layout in drawer {self.__class__.__name__} is empty - skipping")
            return page_image
        if len(self.layout) < page_num:
            print(f"Error! Page {page_num} not found in layout (pages: {len(self.layout)})")
            return page_image
        page_layout = self.layout[page_num - 1]
        for layout_element in page_layout:
            element_type = layout_element.type
            element_prob = layout_element.prob
            color = self.get_element_type_color(element_type)
            bbox = BBox(
                points=(
                    layout_element.bbox.x1,
                    layout_element.bbox.y1,
                    layout_element.bbox.x2,
                    layout_element.bbox.y2,
                ),
                labels=BboxLabels(
                    top_left=f"{element_type}",
                    top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                ),
            )
            draw_bbox_on_image(page_image, bbox, color=color)
        return page_image

    def get_element_type_color(self, element_type: str) -> tuple[int, int, int]:
        return get_rgb_color(self.color_map.get(element_type, "cyan"))


class OCRLayoutDrawer(SimpleLayoutDrawer):
    layout_source = "ocr"

    def __init__(self, color: tuple[int, int, int] = (255, 0, 0)):
        self.color = color
        self.layout: list[list[TextRegion]] = []
        self.show_order = False
        self.show_text_length = False

    def add_ocred_page(self, page_layout: list[TextRegion]):
        self.layout.append(copy.deepcopy(page_layout))


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

    def __init__(self, layout: List[Element]):
        self.layout = layout

    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
        elements_for_page = [
            element for element in self.layout if element.metadata.page_number == page_num
        ]
        for idx, element in enumerate(elements_for_page):
            element_order = idx + 1
            element_type = (
                element.category if isinstance(element, Text) else str(element.__class__.__name__)
            )
            element_prob = getattr(element.metadata, "detection_class_prob", None)
            text_len = len(element.text)
            bbox_points = coordinates_to_bbox(element.metadata.coordinates)
            color = self.get_element_type_color(element_type)
            cluster = getattr(element.metadata, "cluster", None)
            bbox = BBox(
                points=bbox_points,
                labels=BboxLabels(
                    top_left=f"{element_type}",
                    top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                    bottom_right=f"len: {text_len}",
                    bottom_left=f"cl: {cluster}" if cluster else None,
                    center=f"{element_order}",
                ),
            )
            draw_bbox_on_image(page_image, bbox, color=color)
        return page_image

    def get_element_type_color(self, element_type: str) -> tuple[int, int, int]:

        return get_rgb_color(self.color_map.get(element_type, "cyan"))


class AnalysisDrawer(AnalysisProcessor):

    def __init__(
        self,
        filename: Union[str, Path],
        save_dir: Union[str, Path],
        draw_caption: bool = True,
        draw_separate_files: bool = True,
    ):
        self.draw_caption = draw_caption
        self.draw_separate_files = draw_separate_files
        self.drawers = []

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
                image = drawer.draw_layout_on_page(orig_image_page.copy(), page_num=page_num)
                if self.draw_caption:
                    image = self.add_caption(
                        image, caption=f"Layout source: {drawer.layout_source}"
                    )
                if self.draw_separate_files:
                    image.save(
                        analysis_save_dir / f"page{page_num}" f"_layout_{drawer.layout_source}.png"
                    )
                else:
                    images_for_grid.append(image)
            if images_for_grid:
                grid_image = self.paste_images_on_grid(images_for_grid)
                grid_image.save(analysis_save_dir / f"page{page_num}_layout_all.png")

    def add_caption(self, image: Image.Image, caption: str):
        image = ImageOps.expand(image, border=45, fill=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(FONT, 52)
        draw.text((20, 45), caption, (0, 0, 0), font=font)
        return image

    def paste_images_on_grid(self, images: list[Image.Image]) -> Image.Image:
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

        return new_im

    def load_source_image(self) -> Generator[Image.Image, None, None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                image_paths = convert_pdf_to_image(
                    self.filename,
                    output_folder=temp_dir,
                    path_only=True,
                )
            except:  # noqa: E722
                # probably got an image instead of pdf - load it directly
                image_paths = [self.filename]

            for image_path in image_paths:
                with Image.open(image_path) as image:
                    yield image
