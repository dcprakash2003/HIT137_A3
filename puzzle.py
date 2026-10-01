"""
puzzle.py
---------
Owner: Prakash Dangi (Game logic)

PuzzleBoard holds the tiles and all the game rules. It knows nothing about
Tkinter, so it can be tested on its own (see the __main__ block at the end).

OOP concepts shown here
* Encapsulation     : the slot list, history, counters and lock flag are
                      private; the GUI only uses public methods/properties.
* Class interaction : PuzzleBoard owns Tile objects and creates
                      Transformation objects.
* Polymorphism      : scramble(), undo_last() and solve() call
                      apply()/undo() on mixed transformation types.
"""

import random

from transformations import (FlipTransformation, InvertTransformation,
                             RotateTransformation, SwapTransformation)


class Difficulty:
    """Settings for one difficulty level (EXTRA feature)."""

    def __init__(self, name, counts, use_invert=False, time_limits=None):
        self.name = name
        self._counts = counts                 # {grid size: number of transforms}
        self.use_invert = use_invert          # adds a 4th transformation type
        self._time_limits = time_limits or {}  # {grid size: seconds}

    def transform_count(self, grid: int) -> int:
        return self._counts[grid]

    def time_limit(self, grid: int):
        """Seconds allowed, or None for no limit."""
        return self._time_limits.get(grid)


# Normal follows the brief exactly: 6 / 12 / 20 transformations.
DIFFICULTIES = {
    "Easy": Difficulty("Easy", {3: 4, 4: 8, 5: 12}),
    "Normal": Difficulty("Normal", {3: 6, 4: 12, 5: 20}),
    "Hard": Difficulty("Hard", {3: 8, 4: 15, 5: 24}, use_invert=True,
                       time_limits={3: 180, 4: 360, 5: 600}),
}


class PuzzleBoard:
    """The game state: which tile is in which slot, moves, hints, etc."""

    MAX_HINTS = 3

    def __init__(self, tiles: list, grid: int):
        if len(tiles) != grid * grid:
            raise ValueError("Number of tiles does not match the grid.")
        self._grid = grid
        self._slots = list(tiles)       # _slots[i] = tile currently in slot i
        self._scramble_history = []     # transformations applied at load time
        self._player_history = []       # transformations made by the player
        self._moves = 0
        self._hints_used = 0
        self._hint = None               # (current_slot, home_slot) or None
        self._locked = False            # True once solved / time is up
        self._solved_by_player = False

    # ------------------------------------------------------------------ #
    # Low-level operations used by Transformation subclasses
    # ------------------------------------------------------------------ #
    def tile_at(self, slot: int):
        self._check_slot(slot)
        return self._slots[slot]

    def swap_slots(self, a: int, b: int) -> None:
        self._check_slot(a)
        self._check_slot(b)
        self._slots[a], self._slots[b] = self._slots[b], self._slots[a]

    def _check_slot(self, slot: int) -> None:
        if not 0 <= slot < len(self._slots):
            raise IndexError(f"Slot {slot} is outside the board.")

    # ------------------------------------------------------------------ #
    # Scrambling
    # ------------------------------------------------------------------ #
    def scramble(self, count: int, use_invert: bool = False) -> list:
        """Apply `count` random transformations, all generated at once.

        Rules (from the brief / rubric):
        * every type (swap, rotate, flip [, invert]) is used at least once
        * the transformation types and targets are random on every load
        * NO tile is targeted twice, so every affected tile ends up wrong
        """
        singles = [RotateTransformation, FlipTransformation]
        if use_invert:
            singles.append(InvertTransformation)

        total_tiles = self._grid * self._grid
        # Start with one of every type so all types always appear.
        kinds = [SwapTransformation] + singles
        if count < len(kinds):
            raise ValueError(f"Need at least {len(kinds)} transformations.")
        tiles_used = 2 + len(singles)
        if tiles_used + (count - len(kinds)) > total_tiles:
            raise ValueError("Too many transformations for this grid size.")

        # Fill the remaining places. A swap uses 2 tiles, so only choose a
        # swap if there will still be enough free tiles for the rest.
        while len(kinds) < count:
            places_left_after = count - len(kinds) - 1
            options = list(singles)
            if total_tiles - tiles_used - 2 >= places_left_after:
                options.append(SwapTransformation)
            kind = random.choice(options)
            kinds.append(kind)
            tiles_used += 2 if kind is SwapTransformation else 1

        random.shuffle(kinds)

        # A shuffled pool of free slots: popping guarantees no repeats.
        free_slots = list(range(total_tiles))
        random.shuffle(free_slots)

        for kind in kinds:
            if kind is SwapTransformation:
                t = SwapTransformation(free_slots.pop(), free_slots.pop())
            elif kind is InvertTransformation:
                t = InvertTransformation(free_slots.pop())
            else:
                t = kind.random(free_slots.pop())   # Rotate / Flip
            t.apply(self)                           # polymorphic call
            self._scramble_history.append(t)

        return list(self._scramble_history)

    # ------------------------------------------------------------------ #
    # Player actions - each returns True if the move was made
    # ------------------------------------------------------------------ #
    def player_swap(self, a: int, b: int) -> bool:
        if a == b:
            return False
        return self._player_move(SwapTransformation(a, b))

    def player_rotate(self, slot: int) -> bool:
        return self._player_move(RotateTransformation(slot, 1))  # 90 deg CW

    def player_flip(self, slot: int) -> bool:
        return self._player_move(
            FlipTransformation(slot, FlipTransformation.HORIZONTAL))

    def player_invert(self, slot: int) -> bool:
        return self._player_move(InvertTransformation(slot))

    def _player_move(self, transformation) -> bool:
        if self._locked:
            return False
        transformation.apply(self)
        self._player_history.append(transformation)
        self._after_move()
        return True

    def undo_last(self) -> bool:
        """EXTRA: undo the player's last move (counts as a move)."""
        if self._locked or not self._player_history:
            return False
        self._player_history.pop().undo(self)       # polymorphic call
        self._after_move()
        return True

    def _after_move(self) -> None:
        self._moves += 1
        self._hint = None                 # blue circles vanish after a move
        if self.is_solved:
            self._locked = True
            self._solved_by_player = True

    # ------------------------------------------------------------------ #
    # Hint and Solve
    # ------------------------------------------------------------------ #
    def hint(self):
        """Pick one incorrect tile. Returns (current_slot, home_slot) or None."""
        if self._locked or self._hints_used >= self.MAX_HINTS:
            return None
        wrong = [i for i, t in enumerate(self._slots) if not t.is_correct_at(i)]
        if not wrong:
            return None
        current = random.choice(wrong)
        self._hint = (current, self._slots[current].home_index)
        self._hints_used += 1
        return self._hint

    def solve(self) -> None:
        """Undo every remaining transformation (player moves first, then the
        scramble, newest first) and clear the moves and score."""
        for t in reversed(self._player_history):
            t.undo(self)
        for t in reversed(self._scramble_history):
            t.undo(self)
        self._player_history.clear()
        self._scramble_history.clear()
        self._moves = 0
        self._hint = None
        self._locked = True
        self._solved_by_player = False

    def lock(self) -> None:
        """Stop accepting input (used when the time limit runs out)."""
        self._locked = True

    # ------------------------------------------------------------------ #
    # Read-only information for the GUI
    # ------------------------------------------------------------------ #
    @property
    def grid(self) -> int:
        return self._grid

    @property
    def moves(self) -> int:
        return self._moves

    @property
    def tiles_left(self) -> int:
        return sum(not t.is_correct_at(i) for i, t in enumerate(self._slots))

    @property
    def is_solved(self) -> bool:
        return self.tiles_left == 0

    @property
    def is_locked(self) -> bool:
        return self._locked

    @property
    def solved_by_player(self) -> bool:
        return self._solved_by_player

    @property
    def hints_used(self) -> int:
        return self._hints_used

    @property
    def hints_left(self) -> int:
        return self.MAX_HINTS - self._hints_used

    @property
    def current_hint(self):
        return self._hint

    @property
    def can_undo(self) -> bool:
        return bool(self._player_history) and not self._locked

    def correct_slots(self) -> list:
        return [i for i, t in enumerate(self._slots) if t.is_correct_at(i)]

    def tile_images(self) -> list:
        return [t.render() for t in self._slots]

    def score(self, seconds: int) -> int:
        """Score for a completed puzzle: start high, lose points for moves,
        hints and time. Solve (or giving up) scores 0."""
        if not self._solved_by_player:
            return 0
        base = 100 * self._grid * self._grid
        return max(0, base - 5 * self._moves - 50 * self._hints_used - seconds)


# ---------------------------------------------------------------------- #
# Quick self-test without the GUI:  python puzzle.py
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    import numpy as np
    from tile import Tile

    for grid in (3, 4, 5):
        for level in DIFFICULTIES.values():
            tiles = [Tile(np.full((10, 10, 3), i, np.uint8), i)
                     for i in range(grid * grid)]
            board = PuzzleBoard(tiles, grid)
            log = board.scramble(level.transform_count(grid), level.use_invert)
            targeted = [p for t in log for p in t.positions()]
            assert len(targeted) == len(set(targeted)), "tile targeted twice"
            assert board.tiles_left == len(targeted)
            board.solve()
            assert board.is_solved and board.moves == 0
            print(f"{grid}x{grid} {level.name:<6}: {len(log)} transforms, "
                  f"{len(targeted)} tiles targeted - OK")
