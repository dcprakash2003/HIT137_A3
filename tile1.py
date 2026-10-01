"""
tile.py
Owner: Prince Nagarkoti (Image processing & tiles)

The Tile class - one square piece of the puzzle.

OOP stuff used here:
- constructor (__init__ saves the pixels and the home slot)
- encapsulation (_rotation, _flipped, _inverted are private and only change
  through methods like rotate_cw() and flip_h())
- methods like render(), reset(), is_correct_orientation()
"""

import cv2
import numpy as np


class Tile:
    """One square piece of the puzzle image.

    The original pixels are never changed. The tile just remembers its
    rotation / flip / invert state and redraws itself from the original in
    render(), so repeated rotating doesn't hurt the quality.

    displayed = rotate_cw^rotation( flip_h^flipped(original) )
    """

    def __init__(self, image: np.ndarray, home_index: int):
        if image is None or image.size == 0:
            raise ValueError("A tile needs a non-empty image.")
        if image.shape[0] != image.shape[1]:
            # has to be square or a 90 degree turn would change the size
            raise ValueError("Tiles must be square.")
        self._original = image.copy()
        self._home_index = home_index
        self._rotation = 0        # clockwise quarter turns, 0 to 3
        self._flipped = False     # mirrored left-right before rotating
        self._inverted = False    # colours inverted (hard mode)

    # read-only properties
    @property
    def home_index(self) -> int:
        """Slot this tile belongs in when solved."""
        return self._home_index

    @property
    def rotation(self) -> int:
        return self._rotation

    @property
    def flipped(self) -> bool:
        return self._flipped

    @property
    def inverted(self) -> bool:
        return self._inverted

    # changing the tile
    def rotate_cw(self, quarter_turns: int = 1) -> None:
        """Rotate clockwise by 90 degrees * quarter_turns."""
        self._rotation = (self._rotation + quarter_turns) % 4

    def flip_h(self) -> None:
        """Mirror left-to-right as the player sees it.

        Flipping after a rotation is the same as flipping first and then
        rotating the other way, so negate the rotation and toggle the flag.
        """
        self._rotation = (-self._rotation) % 4
        self._flipped = not self._flipped

    def flip_v(self) -> None:
        """Mirror top-to-bottom as the player sees it.

        Same as a horizontal flip plus a 180 degree turn, which gives
        rotation = (2 - rotation) and a toggled flip flag.
        """
        self._rotation = (2 - self._rotation) % 4
        self._flipped = not self._flipped

    def invert(self) -> None:
        """Swap the colours to a negative. Doing it twice undoes it."""
        self._inverted = not self._inverted

    def reset(self) -> None:
        """Back to the original orientation and colours."""
        self._rotation = 0
        self._flipped = False
        self._inverted = False

    # checks
    def is_correct_orientation(self) -> bool:
        """True if the tile looks like the original piece."""
        return self._rotation == 0 and not self._flipped and not self._inverted

    def is_correct_at(self, slot_index: int) -> bool:
        """True if the tile is in its own slot and the right way up."""
        return slot_index == self._home_index and self.is_correct_orientation()

    def render(self) -> np.ndarray:
        """Make the tile image (BGR array) for the current state."""
        img = self._original
        if self._flipped:
            img = cv2.flip(img, 1)  # 1 = horizontal
        for _ in range(self._rotation):
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if self._inverted:
            img = cv2.bitwise_not(img)
        return img.copy()

    def __repr__(self) -> str:
        return (f"Tile(home={self._home_index}, rot={self._rotation * 90}, "
                f"flipped={self._flipped}, inverted={self._inverted})")
