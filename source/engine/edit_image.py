from typing import Tuple, Union

import cv2
import numpy as np

from .input_controller import InputController


Rect = Tuple[int, int, int, int]

def _scale_coords(comp: float, *args: Union[int, float]) -> Tuple[int, ...]:
    return tuple(int(val * comp) for val in args)


def crop(ctrl: InputController, image: np.ndarray, region: Rect) -> np.ndarray:
    """Crops an image based on a logical region and a scale factor."""
    comp = ctrl.comp
    x, y, w, h = _scale_coords(comp, *region)
    return image[y:y+h, x:x+w]

def resize(image: np.ndarray, scale_factors: Tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
    """Resizes an image using area interpolation (downscaling)."""
    fx, fy = scale_factors
    return cv2.resize(image, None, fx=fx, fy=fy, interpolation=cv2.INTER_AREA)

def draw_rect(
        image: np.ndarray, region: Rect, comp: float = 1.0,
        color: cv2.typing.Scalar = (0, 0, 0), thickness: int = -1
        ) -> np.ndarray:
    """Draws a rectangle using logical region scaled to the image size."""
    x, y, w, h = _scale_coords(comp, *region)
    return cv2.rectangle(image, (x, y), (x+w, y+h), color, thickness)