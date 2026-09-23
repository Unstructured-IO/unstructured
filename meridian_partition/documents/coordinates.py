from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Sequence, Tuple, Union


class Orientation(Enum):
    SCREEN = (1, -1)  # Origin in top left, y increases in the down direction
    CARTESIAN = (1, 1)  # Origin in bottom left, y increases in upward direction


def convert_coordinate(old_t, old_t_max, new_t_max, t_orientation):
    """Convert a coordinate into another system along an axis using a linear transformation"""
    return (
        (1 - old_t / old_t_max) * (1 - t_orientation) / 2
        + old_t / old_t_max * (1 + t_orientation) / 2
    ) * new_t_max


class CoordinateSystem:
    """A finite coordinate plane with given width and height."""

    orientation: Orientation

    def __init__(self, width: Union[int, float], height: Union[int, float]):
        self.width = width
        self.height = height

    def __eq__(self, other: object):
        if not isinstance(other, CoordinateSystem):
            return False
        return (
            str(self.__class__.__name__) == str(other.__class__.__name__)
            and self.width == other.width
            and self.height == other.height
            and self.orientation == other.orientation
        )

    def convert_from_relative(
        self,
        x: Union[float, int],
        y: Union[float, int],
    ) -> Tuple[Union[float, int], Union[float, int]]:
        """Convert to this coordinate system from a relative coordinate system."""
        x_orientation, y_orientation = self.orientation.value
        new_x = convert_coordinate(x, 1, self.width, x_orientation)
        new_y = convert_coordinate(y, 1, self.height, y_orientation)
        return new_x, new_y

    def convert_to_relative(
        self,
        x: Union[float, int],
        y: Union[float, int],
    ) -> Tuple[Union[float, int], Union[float, int]]:
        """Convert from this coordinate system to a relative coordinate system."""
        x_orientation, y_orientation = self.orientation.value
        new_x = convert_coordinate(x, self.width, 1, x_orientation)
        new_y = convert_coordinate(y, self.height, 1, y_orientation)
        return new_x, new_y

    def convert_coordinates_to_new_system(
        self,
        new_system: CoordinateSystem,
        x: Union[float, int],
        y: Union[float, int],
    ) -> Tuple[Union[float, int], Union[float, int]]:
        """Convert from this coordinate system to another given coordinate system."""
        rel_x, rel_y = self.convert_to_relative(x, y)
        return new_system.convert_from_relative(rel_x, rel_y)

    def convert_multiple_coordinates_to_new_system(
        self,
        new_system: CoordinateSystem,
        coordinates: Sequence[Tuple[Union[float, int], Union[float, int]]],
    ) -> Tuple[Tuple[Union[float, int], Union[float, int]], ...]:
        """Convert (x, y) coordinates from current system to another coordinate system."""
        new_system_coordinates = []
        for x, y in coordinates:
            new_system_coordinates.append(
                self.convert_coordinates_to_new_system(new_system=new_system, x=x, y=y),
            )
        return tuple(new_system_coordinates)


class RelativeCoordinateSystem(CoordinateSystem):
    """Relative coordinate system where x and y are on a scale from 0 to 1."""

    orientation = Orientation.CARTESIAN

    def __init__(self):
        self.width = 1
        self.height = 1


class PixelSpace(CoordinateSystem):
    """Coordinate system representing a pixel space, such as an image. The origin is at the top
    left."""

    orientation = Orientation.SCREEN


class PointSpace(CoordinateSystem):
    """Coordinate system representing a point space, such as a pdf. The origin is at the bottom
    left."""

    orientation = Orientation.CARTESIAN


TYPE_TO_COORDINATE_SYSTEM_MAP: Dict[str, Any] = {
    "PixelSpace": PixelSpace,
    "PointSpace": PointSpace,
    "CoordinateSystem": CoordinateSystem,
}
