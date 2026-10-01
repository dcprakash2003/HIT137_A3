"""
transformations.py
------------------
Owner: Prakash Dangi(Game logic)

The transformation class hierarchy.

OOP concepts shown here
* Inheritance  : SwapTransformation, RotateTransformation, FlipTransformation
                 and InvertTransformation all inherit from Transformation.
* Abstraction  : Transformation is an abstract base class (ABC) - it defines
                 WHAT every transformation must do, not HOW.
* Polymorphism : the board calls t.apply(board) / t.undo(board) on a list of
                 mixed transformation objects without knowing their type.
                 Each subclass behaves differently for the same call.
                 This is used for scrambling, the Undo button and Solve.
"""

import random
from abc import ABC, abstractmethod


class Transformation(ABC):
    """Base class for anything that changes the puzzle board."""

    @abstractmethod
    def apply(self, board) -> None:
        """Perform the change on the board."""

    @abstractmethod
    def undo(self, board) -> None:
        """Reverse exactly what apply() did."""

    @abstractmethod
    def positions(self) -> tuple:
        """Slot indexes this transformation targets."""

    @abstractmethod
    def describe(self) -> str:
        """Human-readable text, e.g. for the console log."""

    def __str__(self) -> str:
        return self.describe()


class SwapTransformation(Transformation):
    """Two tiles exchange positions."""

    def __init__(self, pos_a: int, pos_b: int):
        if pos_a == pos_b:
            raise ValueError("A swap needs two different positions.")
        self._a = pos_a
        self._b = pos_b

    def apply(self, board) -> None:
        board.swap_slots(self._a, self._b)

    def undo(self, board) -> None:
        board.swap_slots(self._a, self._b)        # swapping again restores it

    def positions(self) -> tuple:
        return (self._a, self._b)

    def describe(self) -> str:
        return f"Swap tiles {self._a} <-> {self._b}"


class RotateTransformation(Transformation):
    """A tile is rotated clockwise by 90, 180 or 270 degrees."""

    VALID_TURNS = (1, 2, 3)

    def __init__(self, pos: int, quarter_turns: int = 1):
        if quarter_turns not in self.VALID_TURNS:
            raise ValueError("Rotation must be 90, 180 or 270 degrees.")
        self._pos = pos
        self._turns = quarter_turns

    @classmethod
    def random(cls, pos: int) -> "RotateTransformation":
        return cls(pos, random.choice(cls.VALID_TURNS))

    def apply(self, board) -> None:
        board.tile_at(self._pos).rotate_cw(self._turns)

    def undo(self, board) -> None:
        board.tile_at(self._pos).rotate_cw(4 - self._turns)

    def positions(self) -> tuple:
        return (self._pos,)

    def describe(self) -> str:
        return f"Rotate tile {self._pos} by {self._turns * 90} degrees"


class FlipTransformation(Transformation):
    """A tile is flipped horizontally or vertically."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"

    def __init__(self, pos: int, axis: str = HORIZONTAL):
        if axis not in (self.HORIZONTAL, self.VERTICAL):
            raise ValueError("Axis must be 'horizontal' or 'vertical'.")
        self._pos = pos
        self._axis = axis

    @classmethod
    def random(cls, pos: int) -> "FlipTransformation":
        return cls(pos, random.choice((cls.HORIZONTAL, cls.VERTICAL)))

    def _do_flip(self, board) -> None:
        tile = board.tile_at(self._pos)
        if self._axis == self.HORIZONTAL:
            tile.flip_h()
        else:
            tile.flip_v()

    def apply(self, board) -> None:
        self._do_flip(board)

    def undo(self, board) -> None:
        self._do_flip(board)                  # a flip is its own inverse

    def positions(self) -> tuple:
        return (self._pos,)

    def describe(self) -> str:
        return f"Flip tile {self._pos} {self._axis}ly"


class InvertTransformation(Transformation):
    """EXTRA (Hard mode): a tile's colours are inverted like a negative."""

    def __init__(self, pos: int):
        self._pos = pos

    def apply(self, board) -> None:
        board.tile_at(self._pos).invert()

    def undo(self, board) -> None:
        board.tile_at(self._pos).invert()

    def positions(self) -> tuple:
        return (self._pos,)

    def describe(self) -> str:
        return f"Invert colours of tile {self._pos}"
