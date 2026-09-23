# Copyright (c) Megvii Inc. All rights reserved.
# Unstructured modified the original source code found at
# https://github.com/Megvii-BaseDetection/YOLOX/blob/ac379df3c97d1835ebd319afad0c031c36d03f36/yolox/utils/visualize.py
import typing
from typing import Optional, Union

import matplotlib.pyplot as plt
import numpy as np
from PIL import ImageFont
from PIL.Image import Image
from PIL.ImageDraw import ImageDraw

from unstructured_inference.inference.elements import TextRegion


@typing.no_type_check
def draw_bbox(
    image: Image,
    element: TextRegion,
    color: str = "red",
    width=1,
    details: bool = False,
) -> Image:
    """Draws bounding box in image"""
    try:
        img = image.copy()
        draw = ImageDraw(img)
        topleft, _, bottomright, _ = element.bbox.coordinates
        c = getattr(element, "color", color)
        if details:
            source = getattr(element, "source", "Unknown")
            type = getattr(element, "type", "")
            kbd = ImageFont.truetype("Keyboard.ttf", 20)
            draw.text(topleft, text=f"{type} {source}", fill=c, font=kbd)
        draw.rectangle((topleft, bottomright), outline=c, width=width)
    except OSError:
        print("Failed to find font file. Skipping details.")
        img = draw_bbox(image, element, color, width)
    except Exception as e:
        print(f"Failed to draw bounding box: {e}")
    return img


def show_plot(
    image: Union[Image, np.ndarray],
    desired_width: Optional[int] = None,
):
    """
    Display an image using matplotlib with an optional desired width while maintaining the aspect
     ratio.

    Parameters:
    - image (Union[Image, np.ndarray]): An image in PIL Image format or a numpy ndarray format.
    - desired_width (Optional[int]): Desired width for the display size of the image.
        If provided, the height is calculated based on the original aspect ratio.
        If not provided, the image will be displayed with its original dimensions.

    Raises:
    - ValueError: If the provided image type is neither PIL Image nor numpy ndarray.

    Returns:
    - None: The function displays the image using matplotlib but does not return any value.
    """
    if isinstance(image, Image):
        image_width, image_height = image.size
    elif isinstance(image, np.ndarray):
        image_height, image_width, _ = image.shape
    else:
        raise ValueError("Unsupported Image Type")

    if desired_width:
        # Calculate the desired height based on the original aspect ratio
        aspect_ratio = image_width / image_height
        desired_height = desired_width / aspect_ratio

        # Create a figure with the desired size and aspect ratio
        fig, ax = plt.subplots(figsize=(desired_width, desired_height))
    else:
        # Create figure and axes
        fig, ax = plt.subplots()
    # Display the image
    ax.imshow(image)
    plt.show()


_COLORS = np.array(
    [
        [0.000, 0.447, 0.741],
        [0.850, 0.325, 0.098],
        [0.929, 0.694, 0.125],
        [0.494, 0.184, 0.556],
        [0.466, 0.674, 0.188],
        [0.301, 0.745, 0.933],
        [0.635, 0.078, 0.184],
        [0.300, 0.300, 0.300],
        [0.600, 0.600, 0.600],
        [1.000, 0.000, 0.000],
        [1.000, 0.500, 0.000],
        [0.749, 0.749, 0.000],
        [0.000, 1.000, 0.000],
        [0.000, 0.000, 1.000],
        [0.667, 0.000, 1.000],
        [0.333, 0.333, 0.000],
        [0.333, 0.667, 0.000],
        [0.333, 1.000, 0.000],
        [0.667, 0.333, 0.000],
        [0.667, 0.667, 0.000],
        [0.667, 1.000, 0.000],
        [1.000, 0.333, 0.000],
        [1.000, 0.667, 0.000],
        [1.000, 1.000, 0.000],
        [0.000, 0.333, 0.500],
        [0.000, 0.667, 0.500],
        [0.000, 1.000, 0.500],
        [0.333, 0.000, 0.500],
        [0.333, 0.333, 0.500],
        [0.333, 0.667, 0.500],
        [0.333, 1.000, 0.500],
        [0.667, 0.000, 0.500],
        [0.667, 0.333, 0.500],
        [0.667, 0.667, 0.500],
        [0.667, 1.000, 0.500],
        [1.000, 0.000, 0.500],
        [1.000, 0.333, 0.500],
        [1.000, 0.667, 0.500],
        [1.000, 1.000, 0.500],
        [0.000, 0.333, 1.000],
        [0.000, 0.667, 1.000],
        [0.000, 1.000, 1.000],
        [0.333, 0.000, 1.000],
        [0.333, 0.333, 1.000],
        [0.333, 0.667, 1.000],
        [0.333, 1.000, 1.000],
        [0.667, 0.000, 1.000],
        [0.667, 0.333, 1.000],
        [0.667, 0.667, 1.000],
        [0.667, 1.000, 1.000],
        [1.000, 0.000, 1.000],
        [1.000, 0.333, 1.000],
        [1.000, 0.667, 1.000],
        [0.333, 0.000, 0.000],
        [0.500, 0.000, 0.000],
        [0.667, 0.000, 0.000],
        [0.833, 0.000, 0.000],
        [1.000, 0.000, 0.000],
        [0.000, 0.167, 0.000],
        [0.000, 0.333, 0.000],
        [0.000, 0.500, 0.000],
        [0.000, 0.667, 0.000],
        [0.000, 0.833, 0.000],
        [0.000, 1.000, 0.000],
        [0.000, 0.000, 0.167],
        [0.000, 0.000, 0.333],
        [0.000, 0.000, 0.500],
        [0.000, 0.000, 0.667],
        [0.000, 0.000, 0.833],
        [0.000, 0.000, 1.000],
        [0.000, 0.000, 0.000],
        [0.143, 0.143, 0.143],
        [0.286, 0.286, 0.286],
        [0.429, 0.429, 0.429],
        [0.571, 0.571, 0.571],
        [0.714, 0.714, 0.714],
        [0.857, 0.857, 0.857],
        [0.000, 0.447, 0.741],
        [0.314, 0.717, 0.741],
        [0.50, 0.5, 0],
    ],
).astype(np.float32)
