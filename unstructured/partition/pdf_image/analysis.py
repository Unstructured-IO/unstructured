import copy
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, TypeVar, Union

import numpy as np
from matplotlib import colors, font_manager
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw, ImageFont, ImageOps
from unstructured_inference.constants import ElementType
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layout import DocumentLayout, PageLayout

from unstructured.documents.elements import Element, Text
from unstructured.partition.pdf_image.pdf_image_utils import convert_pdf_to_image
from unstructured.partition.utils.sorting import coordinates_to_bbox
from unstructured_inference.inference.layoutelement import LayoutElement

PageImage = TypeVar("PageImage", Image.Image, np.ndarray)


def get_font():
    preffered_fonts = ["Arial.ttf"]
    available_fonts = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    for font in preffered_fonts:
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
    rgb_colors = colors.to_rgb(color)
    return int(rgb_colors[0] * 255), int(rgb_colors[1] * 255), int(rgb_colors[2] * 255)


def generate_color_mapping(classes: list[str]) -> dict[str, tuple[int, ...]]:
    """Generate a unique BGR color for each class

    :param num_classes: The number of classes in the dataset.
    :return:            List of RGB colors for each class.
    """
    cmap = plt.cm.get_cmap("gist_rainbow", len(classes))
    colors = [cmap(i, bytes=True)[:3][::-1] for i in range(len(classes))]
    return {clazz: tuple(int(v) for v in color) for color, clazz in zip(colors, classes)}


def get_recommended_text_size(x1: int, y1: int, x2: int, y2: int) -> int:
    """Get a nice text size for a given bounding box."""
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    diag_length = np.sqrt(bbox_width**2 + bbox_height**2)
    # create a linear function that maps the diagonal length to the font size
    # - diag_length=100 -> base_font_size=16 (min text size)
    # - diag_length=300 -> base_font_size=52 (max text size)
    coefficients = np.polyfit((100, 16), (500, 32), 1)
    font_size = int(diag_length * coefficients[0] + coefficients[1])
    font_size = min(32, font_size)
    font_size = max(16, font_size)

    return font_size


def get_recommended_box_thickness(x1: int, y1: int, x2: int, y2: int) -> int:
    """Get a nice box thickness for a given bounding box."""
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    diag_length = np.sqrt(bbox_width**2 + bbox_height**2)

    if diag_length <= 100:
        return 1
    elif diag_length <= 200:
        return 2
    else:
        return 3


def compute_brightness(color: tuple[int, int, int]) -> float:
    """Computes the brightness of a given color in RGB format.
    From https://alienryderflex.com/hsp.html

    Args:
        color: RGB values of the color.

    Returns:
        The brightness of the color in the range [0, 1].
    """
    return (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[0]) / 255


def best_text_color(
    background_color: tuple[int, int, int], color_threshold: float = 0.5
) -> tuple[int, int, int]:
    """Returns the best text color (black or white) for a given background color.

    Args:
        background_color: RGB values of the background color.

    Returns:
        The RGB values of the best text color, either black or white.
    """
    if compute_brightness(background_color) > color_threshold:
        return (0, 0, 0)
    else:
        return (255, 255, 255)


def get_text_bbox(
    alignment: TextAlignment,
    bbox_points: tuple[int, int, int, int],
    text_width: int,
    text_height: int,
):
    text_offset = 7
    x1, y1, x2, y2 = bbox_points
    correction = int(text_height * 0.3)
    if alignment is TextAlignment.CENTER:
        # center:
        # resize text width and height by 20% to make it look better
        horizontal_half = text_width // 2 + text_offset
        vertical_half = text_height // 2
        center_point = x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2
        text_rectangle = (
            (
                center_point[0] - int(horizontal_half * 1.05),
                center_point[1] - int(vertical_half * 1.05) - correction,
            ),
            (
                center_point[0] + int(horizontal_half * 1.05),
                center_point[1] + int(vertical_half * 1.05) + correction,
            ),
        )
        text_xy = (
            center_point[0] - text_width // 2,
            center_point[1] - int(vertical_half * 1.05) - correction,
        )
    elif alignment is TextAlignment.TOP_LEFT:
        text_rectangle = (
            (x1, y1 - text_height - correction),
            (x1 + text_width + text_offset * 2, y1),
        )
        text_xy = (x1 + text_offset, y1 - text_height - correction)
    elif alignment is TextAlignment.TOP_RIGHT:
        text_rectangle = (
            (x2 - text_width - text_offset * 2, y1),
            (x2, y1 + text_height + correction),
        )
        text_xy = (x2 - text_width - text_offset, y1)
    elif alignment is TextAlignment.BOTTOM_LEFT:
        text_rectangle = (
            (x1, y2 - text_height - correction),
            (x1 + text_width + text_offset * 2, y2),
        )
        text_xy = (x1 + text_offset, y2 - text_height - correction)
    elif alignment is TextAlignment.BOTTOM_RIGHT:
        text_rectangle = (
            (x2 - text_width - text_offset * 2, y2 - text_height - correction),
            (x2, y2),
        )
        text_xy = (x2 - text_width - text_offset, y2 - text_height - correction)
    else:
        raise ValueError(f"Unknown alignment {alignment}")
    return text_rectangle, text_xy


def draw_text_box(
    image: Image.Image,
    text: str,
    bbox_points: tuple[int, int, int, int],
    alignment: TextAlignment,
    font_size: int,
    background_color: tuple[int, int, int],
) -> Image.Image:
    """Draw a text box on an image.

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

    text_rectangle, text_xy = get_text_bbox(alignment, bbox_points, text_width, text_height)

    # Draw the text box
    draw.rectangle(
        text_rectangle,
        fill=background_color,
        outline=background_color,
    )

    # Draw the text
    draw.text(text_xy, text, fill=best_text_color(background_color), font=font, align="center")

    return image


def draw_bbox_on_image(image: Image.Image, bbox: BBox, color: tuple[int, int, int]) -> Image.Image:
    """Draw a bounding box on an image.

    Args:
        image:          Image on which to draw the bounding box.
        bbox:           Bounding box to draw.
        color:          RGB values of the color of the bounding box.
        box_thickness:  Thickness of the bounding box border.

    Returns:
        The image with the bounding box drawn.
    """
    x1, y1, x2, y2 = bbox.points
    top_left_label = x1, y1
    bottom_right = x2, y2

    box_thickness = get_recommended_box_thickness(x1=x1, y1=y1, x2=x2, y2=y2)
    font_size = get_recommended_text_size(x1=x1, y1=y1, x2=x2, y2=y2)

    draw = ImageDraw.ImageDraw(image)
    draw.rectangle((top_left_label, bottom_right), outline=color, width=box_thickness)

    if bbox.labels is not None:
        if top_left_label := bbox.labels.top_left:
            draw_text_box(
                image,
                top_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if top_right_label := bbox.labels.top_right:
            draw_text_box(
                image,
                top_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.TOP_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_left_label := bbox.labels.bottom_left:
            draw_text_box(
                image,
                bottom_left_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_LEFT,
                font_size=font_size,
                background_color=color,
            )
        if bottom_right_label := bbox.labels.bottom_right:
            draw_text_box(
                image,
                bottom_right_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.BOTTOM_RIGHT,
                font_size=font_size,
                background_color=color,
            )
        if center_label := bbox.labels.center:
            draw_text_box(
                image,
                center_label,
                bbox_points=bbox.points,
                alignment=TextAlignment.CENTER,
                font_size=font_size * 2,
                background_color=color,
            )


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

class PdftextLayoutDrawer(SimpleLayoutDrawer):
    layout_source = "pdftext"

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
        self.layout: list[LayoutElement] = copy.deepcopy([page.elements for page in layout.pages])

    def draw_layout_on_page(self, page_image: Image.Image, page_num: int) -> Image.Image:
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
                    #top_right=f"prob: {element_prob:.2f}" if element_prob else None,
                    #bottom_right=f"len: {text_len}",
                    bottom_left=f"cl: {cluster}" if cluster else None,
                    center=f"{element_order}",
                ),
            )
            draw_bbox_on_image(page_image, bbox, color=color)
        return page_image

    def get_element_type_color(self, element_type: str) -> tuple[int, int, int]:

        return get_rgb_color(self.color_map.get(element_type, "cyan"))


class AnalysisDrawer:

    def __init__(
        self,
        filename: Union[str, Path],
        save_dir: Union[str, Path],
        draw_caption: bool = True,
        draw_separate_files: bool = True,
    ):
        self.filename = filename
        self.save_dir = save_dir
        self.draw_caption = draw_caption
        self.draw_separate_files = draw_separate_files
        self.drawers = []

    def add_drawer(self, drawer: LayoutDrawer):
        self.drawers.append(drawer)

    def save_layouts(self):

        filename_stem = Path(self.filename).stem

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
                        f"{self.save_dir}/{filename_stem}_page{page_num}"
                        f"_layout_{drawer.layout_source}.png"
                    )
                else:
                    images_for_grid.append(image)
            if images_for_grid:
                grid_image = self.paste_images_on_grid(images_for_grid)
                grid_image.save(f"{self.save_dir}/{filename_stem}_page{page_num}_layout_all.png")

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

    def load_source_image(self) -> Image.Image:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = convert_pdf_to_image(
                self.filename,
                output_folder=temp_dir,
                path_only=True,
            )
            for image_path in image_paths:
                with Image.open(image_path) as image:
                    yield image
