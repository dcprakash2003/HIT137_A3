"""
gui.py
------
Owner: Kritika GC (GUI & integration)

The Tkinter user interface.

OOP concepts shown here
* Inheritance  : PuzzleApp inherits from tk.Tk.
                 ImagePanel inherits from tk.Canvas, and OriginalPanel /
                 PuzzlePanel inherit from ImagePanel.
* Polymorphism : every panel answers placeholder_text() differently, and
                 the app calls panel.clear() on both without caring which
                 kind it is.
* Encapsulation: widgets, timers and game state are private attributes.
* Class interaction: PuzzleApp -> ImageProcessor -> Tile
                     PuzzleApp -> PuzzleBoard -> Transformation subclasses
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from image_processor import ImageLoadError, ImageProcessor
from puzzle import DIFFICULTIES, PuzzleBoard

DISPLAY_SIZE = 420          # divisible by 3, 4 and 5 -> equal tiles
GRID_CHOICES = {"3 x 3": 3, "4 x 4": 4, "5 x 5": 5}


# ====================================================================== #
# Image panels
# ====================================================================== #
class ImagePanel(tk.Canvas):
    """Base class: a square canvas that can show an OpenCV (BGR) image."""

    def __init__(self, master, size: int):
        super().__init__(master, width=size, height=size, bg="#2b2b2b",
                         highlightthickness=0, bd=0)
        self._size = size
        self._photo = None           # keep a reference or Tk drops the image
        self._image_side = 0         # width/height of the image on screen
        self.clear()

    def placeholder_text(self) -> str:
        """Text shown when no image is loaded. Overridden by subclasses."""
        return "No image"

    def clear(self) -> None:
        self.delete("all")
        self._photo = None
        self._image_side = 0
        self.create_text(self._size // 2, self._size // 2,
                         text=self.placeholder_text(), fill="#cccccc",
                         font=("Segoe UI", 12), justify="center",
                         width=self._size - 40)

    def show(self, image_bgr) -> None:
        """Display a BGR numpy image in the top-left corner of the canvas."""
        rgb = ImageProcessor.to_rgb(image_bgr)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._photo)
        self._image_side = image_bgr.shape[0]


class OriginalPanel(ImagePanel):
    """Left panel - the untouched picture, for reference only (no clicks)."""

    def placeholder_text(self) -> str:
        return "The original image will appear here\n(reference only)"


class PuzzlePanel(ImagePanel):
    """Right panel - the scrambled picture. The only panel that reacts to
    the mouse. It turns a pixel click into a tile index and passes it on."""

    def __init__(self, master, size, on_select, on_rotate, on_flip,
                 on_invert):
        super().__init__(master, size)
        self._grid = 3
        self._on_select = on_select
        self._on_rotate = on_rotate
        self._on_flip = on_flip
        self._on_invert = on_invert
        # Left click = select / swap, Shift+left = flip,
        # Right click = rotate (Button-2 is right click on macOS),
        # Shift+right = invert colours (Hard mode).
        # Tk always runs the MOST specific binding, so Shift+click does not
        # also trigger the plain click handler.
        self.bind("<Button-1>", lambda e: self._dispatch(e, self._on_select))
        self.bind("<Shift-Button-1>", lambda e: self._dispatch(e, self._on_flip))
        for button in ("<Button-2>", "<Button-3>"):
            self.bind(button, lambda e: self._dispatch(e, self._on_rotate))
        for button in ("<Shift-Button-2>", "<Shift-Button-3>"):
            self.bind(button, lambda e: self._dispatch(e, self._on_invert))

    def placeholder_text(self) -> str:
        return "Choose a grid size, then click\n'Load Image' to start a puzzle"

    def set_grid(self, grid: int) -> None:
        self._grid = grid

    def index_at(self, x: int, y: int):
        """Convert canvas pixel (x, y) into a tile index, or None if the
        click was outside the picture."""
        side = self._image_side
        if side == 0 or not (0 <= x < side and 0 <= y < side):
            return None
        tile = side // self._grid
        col = min(x // tile, self._grid - 1)
        row = min(y // tile, self._grid - 1)
        return row * self._grid + col

    def _dispatch(self, event, callback):
        index = self.index_at(event.x, event.y)
        if index is not None:          # clicks outside the image are ignored
            callback(index)
        return "break"


# ====================================================================== #
# Main window
# ====================================================================== #
class PuzzleApp(tk.Tk):
    """The main window. Connects the widgets to the game logic."""

    def __init__(self):
        super().__init__()
        self.title("HIT137 Tile Puzzle")
        self.resizable(False, False)
        self.configure(padx=12, pady=10)

        self._processor = ImageProcessor(DISPLAY_SIZE)
        self._board = None              # PuzzleBoard for the current round
        self._source_image = None       # image as loaded from disk
        self._square_image = None       # resized + cropped original
        self._image_name = ""
        self._grid = 3
        self._difficulty = DIFFICULTIES["Normal"]
        self._selected = None           # selected slot index or None
        self._seconds = 0
        self._timer_id = None
        self._best_scores = {}          # (grid, difficulty) -> best score

        self._build_controls()
        self._build_panels()
        self._build_status()
        self._bind_shortcuts()
        self._update_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(bar, text="Grid:").pack(side="left")
        self._grid_var = tk.StringVar(value="3 x 3")      # default 3x3
        ttk.Combobox(bar, textvariable=self._grid_var, width=6,
                     state="readonly", values=list(GRID_CHOICES)
                     ).pack(side="left", padx=(4, 12))

        ttk.Label(bar, text="Difficulty:").pack(side="left")
        self._level_var = tk.StringVar(value="Normal")
        ttk.Combobox(bar, textvariable=self._level_var, width=8,
                     state="readonly", values=list(DIFFICULTIES)
                     ).pack(side="left", padx=(4, 12))

        self._load_btn = ttk.Button(bar, text="Load Image",
                                    command=self.load_image)
        self._restart_btn = ttk.Button(bar, text="New Scramble",
                                       command=self.restart)
        self._hint_btn = ttk.Button(bar, text="Hint (3)", command=self.hint)
        self._undo_btn = ttk.Button(bar, text="Undo", command=self.undo)
        self._solve_btn = ttk.Button(bar, text="Solve", command=self.solve)
        for btn in (self._load_btn, self._restart_btn, self._hint_btn,
                    self._undo_btn, self._solve_btn):
            btn.pack(side="left", padx=3)

    def _build_panels(self):
        area = ttk.Frame(self)
        area.pack()

        left = ttk.LabelFrame(area, text=" Original (reference) ", padding=6)
        right = ttk.LabelFrame(area, text=" Puzzle (click here) ", padding=6)
        left.grid(row=0, column=0, padx=(0, 8))
        right.grid(row=0, column=1)

        self._original_panel = OriginalPanel(left, DISPLAY_SIZE)
        self._puzzle_panel = PuzzlePanel(
            right, DISPLAY_SIZE,
            on_select=self._on_select, on_rotate=self._on_rotate,
            on_flip=self._on_flip, on_invert=self._on_invert)
        self._original_panel.pack()
        self._puzzle_panel.pack()

    def _build_status(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(8, 0))
        self._moves_lbl = ttk.Label(bar, font=("Segoe UI", 11, "bold"))
        self._left_lbl = ttk.Label(bar, font=("Segoe UI", 11, "bold"))
        self._time_lbl = ttk.Label(bar, font=("Segoe UI", 11))
        self._score_lbl = ttk.Label(bar, font=("Segoe UI", 11))
        for lbl in (self._moves_lbl, self._left_lbl, self._time_lbl,
                    self._score_lbl):
            lbl.pack(side="left", padx=(0, 22))

        self._message_lbl = ttk.Label(self, foreground="#555555")
        self._message_lbl.pack(fill="x", pady=(4, 0))
        ttk.Label(self, foreground="#777777", text=(
            "Left click: select / swap    Right click: rotate 90°    "
            "Shift + left click: flip    Shift + right click: invert colours "
            "(Hard)    Ctrl+O: load    Ctrl+Z: undo")).pack(fill="x")

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.load_image())
        self.bind("<Control-z>", lambda e: self.undo())

    # ------------------------------------------------------------------ #
    # Loading / starting a round
    # ------------------------------------------------------------------ #
    def load_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"),
                       ("JPEG", "*.jpg *.jpeg"), ("PNG", "*.png"),
                       ("Bitmap", "*.bmp"), ("All files", "*.*")])
        if not path:                                    # dialog cancelled
            self._say("Loading cancelled - no image was changed.")
            return
        try:
            image = self._processor.load(path)
        except ImageLoadError as exc:
            messagebox.showerror("Cannot open image", str(exc), parent=self)
            return
        self._source_image = image
        self._image_name = os.path.basename(path)
        self._start_round()

    def restart(self):
        """Re-scramble the same image with the current grid / difficulty."""
        if self._source_image is None:
            self._say("Load an image first.")
            return
        self._start_round()

    def _start_round(self):
        grid = GRID_CHOICES[self._grid_var.get()]
        difficulty = DIFFICULTIES[self._level_var.get()]
        try:
            square = self._processor.fit_to_grid(self._source_image, grid)
        except ImageLoadError as exc:
            messagebox.showerror("Image too small", str(exc), parent=self)
            return

        # Everything below fully resets the round.
        self._grid, self._difficulty = grid, difficulty
        self._square_image = square
        self._board = PuzzleBoard(self._processor.split(square, grid), grid)
        log = self._board.scramble(difficulty.transform_count(grid),
                                   difficulty.use_invert)
        print(f"\nNew round: {self._image_name}, {grid}x{grid}, "
              f"{difficulty.name}")
        for t in log:
            print("  ", t)                   # polymorphic describe()

        self._selected = None
        self._puzzle_panel.set_grid(grid)
        self._restart_timer()
        self._say(f"Loaded '{self._image_name}' - {grid}x{grid}, "
                  f"{difficulty.name}, {len(log)} transformations applied.")
        self._refresh()

    # ------------------------------------------------------------------ #
    # Mouse actions (called by PuzzlePanel with a tile index)
    # ------------------------------------------------------------------ #
    def _can_play(self) -> bool:
        if self._board is None:
            self._say("Load an image to start playing.")
            return False
        if self._board.is_locked:
            self._say("This puzzle is finished - load another image "
                      "or press New Scramble.")
            return False
        return True

    def _on_select(self, index):
        if not self._can_play():
            return
        if self._selected is None:               # first click: select
            self._selected = index
            self._refresh()
        elif self._selected == index:            # same tile: deselect
            self._selected = None
            self._refresh()
        else:                                    # second tile: swap
            first, self._selected = self._selected, None
            self._board.player_swap(first, index)
            self._after_move()

    def _on_rotate(self, index):
        if self._can_play():
            self._board.player_rotate(index)
            self._after_move()

    def _on_flip(self, index):
        if self._can_play():
            self._board.player_flip(index)
            self._after_move()

    def _on_invert(self, index):
        if not self._can_play():
            return
        if not self._difficulty.use_invert:
            self._say("Colour inversion is only used in Hard mode.")
            return
        self._board.player_invert(index)
        self._after_move()

    def _after_move(self):
        self._refresh()
        if self._board.solved_by_player:
            self._finish_round()

    # ------------------------------------------------------------------ #
    # Buttons
    # ------------------------------------------------------------------ #
    def hint(self):
        if not self._can_play():
            return
        result = self._board.hint()
        if result is None:
            self._say("No hints left for this image.")
        else:
            self._say(f"Hint: the circled tile belongs where the circle is "
                      f"on the original. {self._board.hints_left} hint(s) "
                      f"left.")
        self._refresh()

    def undo(self):
        if self._board is not None and self._board.undo_last():
            self._say("Last move undone.")
            self._after_move()

    def solve(self):
        # Allowed while playing AND after the time limit runs out.
        if self._board is None or self._board.is_solved:
            return
        self._board.solve()
        self._selected = None
        self._stop_timer()
        self._refresh()
        self._say("Solved with the Solve button - moves and score cleared.")
        messagebox.showinfo(
            "Puzzle solved",
            "All transformations have been undone.\n"
            "Moves and score have been cleared.\n\n"
            "Load another image (or press New Scramble) to play again.",
            parent=self)

    def _finish_round(self):
        self._stop_timer()
        self._selected = None
        score = self._board.score(self._seconds)
        key = (self._grid, self._difficulty.name)
        best = self._best_scores.get(key)
        new_best = best is None or score > best
        if new_best:
            self._best_scores[key] = score
        self._refresh()
        self._say("Puzzle complete! Load another image to keep playing.")
        messagebox.showinfo(
            "Well done!",
            f"You restored the picture!\n\n"
            f"Moves: {self._board.moves}\n"
            f"Time: {self._format_time(self._seconds)}\n"
            f"Hints used: {self._board.hints_used}\n"
            f"Score: {score}" + ("   (new best!)" if new_best else ""),
            parent=self)

    # ------------------------------------------------------------------ #
    # Timer (EXTRA) - with a time limit in Hard mode
    # ------------------------------------------------------------------ #
    def _restart_timer(self):
        self._stop_timer()
        self._seconds = 0
        self._timer_id = self.after(1000, self._tick)

    def _stop_timer(self):
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _tick(self):
        self._seconds += 1
        self._update_status()
        limit = self._difficulty.time_limit(self._grid)
        if limit is not None and self._seconds >= limit:
            self._timer_id = None
            self._board.lock()
            self._selected = None
            self._refresh()
            self._say("Time is up! Press Solve to see the answer, "
                      "or load another image.")
            messagebox.showwarning("Time is up",
                                   "You ran out of time for this puzzle.",
                                   parent=self)
            return
        self._timer_id = self.after(1000, self._tick)

    @staticmethod
    def _format_time(seconds: int) -> str:
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def _refresh(self):
        """Re-render both images and the counters after every action."""
        if self._board is None:
            for panel in (self._original_panel, self._puzzle_panel):
                panel.clear()                     # polymorphic placeholder
            self._update_status()
            return

        p, grid, board = self._processor, self._grid, self._board

        puzzle = p.assemble(board.tile_images(), grid)
        puzzle = p.draw_grid(puzzle, grid)
        for slot in board.correct_slots():
            puzzle = p.draw_tick(puzzle, grid, slot)
        if self._selected is not None:
            puzzle = p.draw_selection(puzzle, grid, self._selected)

        original = self._square_image
        if board.current_hint is not None:
            current, home = board.current_hint
            puzzle = p.draw_circle(puzzle, grid, current)
            original = p.draw_circle(original, grid, home)

        self._original_panel.show(original)
        self._puzzle_panel.show(puzzle)
        self._update_status()

    def _update_status(self):
        board = self._board
        if board is None:
            self._moves_lbl.config(text="Moves: 0")
            self._left_lbl.config(text="Tiles left: -")
            self._time_lbl.config(text="Time: 00:00")
            self._score_lbl.config(text="Score: -")
            for btn in (self._restart_btn, self._hint_btn, self._undo_btn,
                        self._solve_btn):
                btn.state(["disabled"])
            return

        self._moves_lbl.config(text=f"Moves: {board.moves}")
        self._left_lbl.config(text=f"Tiles left: {board.tiles_left}")

        limit = self._difficulty.time_limit(self._grid)
        if limit is None:
            self._time_lbl.config(text=f"Time: {self._format_time(self._seconds)}")
        else:
            remaining = max(0, limit - self._seconds)
            self._time_lbl.config(
                text=f"Time left: {self._format_time(remaining)}")

        best = self._best_scores.get((self._grid, self._difficulty.name))
        score = board.score(self._seconds) if board.is_locked else None
        self._score_lbl.config(
            text=f"Score: {'-' if score is None else score}   "
                 f"Best: {'-' if best is None else best}")

        self._hint_btn.config(text=f"Hint ({board.hints_left})")
        playing = not board.is_locked
        self._restart_btn.state(["!disabled"])
        self._hint_btn.state(["!disabled" if playing and board.hints_left
                              else "disabled"])
        self._undo_btn.state(["!disabled" if board.can_undo else "disabled"])
        # Solve stays available after time runs out (to reveal the answer).
        self._solve_btn.state(["!disabled" if not board.is_solved
                               else "disabled"])

    def _say(self, text: str):
        self._message_lbl.config(text=text)

    # ------------------------------------------------------------------ #
    # Error handling and closing
    # ------------------------------------------------------------------ #
    def report_callback_exception(self, exc_type, exc_value, exc_tb):
        """Any unexpected error inside a Tk callback is shown in a message
        box instead of crashing silently in the console."""
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)
        messagebox.showerror("Unexpected error",
                             f"Something went wrong:\n{exc_value}",
                             parent=self)

    def _on_close(self):
        self._stop_timer()
        self.destroy()
