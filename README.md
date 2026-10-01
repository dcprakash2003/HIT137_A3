# HIT137 Assignment 3 – Tile Puzzle (Tkinter + OpenCV)

A desktop game that loads an image, cuts it into a grid of tiles and scrambles it
with random **swaps, rotations and flips**. The player restores the picture
using the mouse.

## How to run

```bash
pip install -r requirements.txt
python main.py
```

Python 3.9+ is needed. Tkinter comes with the standard Python installer on
Windows and macOS. On Linux, install it with `sudo apt install python3-tk`.

## Controls

| Action | What it does |
|---|---|
| Left click a tile | Select it (coloured border). Click a second tile to swap. Click the same tile again to deselect. |
| Right click | Rotate the tile 90° clockwise |
| Shift + left click | Flip the tile horizontally |
| Shift + right click | Invert the tile's colours (Hard mode only) |
| Hint | Blue circle on one wrong tile and on its home position on the original. Limited to 3 per image. |
| Undo / Ctrl+Z | Undo your last move (this counts as a move) |
| Solve | Instantly undoes every remaining transformation and clears moves and score |
| New Scramble | Re-scrambles the same image with the current grid and difficulty |

## Features mapped to the brief and rubric

| Requirement | Where |
|---|---|
| Encapsulation, constructors, methods | `Tile` (private orientation state), `PuzzleBoard` (private slots, history, counters) |
| Inheritance | `Transformation` → `Swap/Rotate/Flip/InvertTransformation`; `tk.Canvas` → `ImagePanel` → `OriginalPanel` / `PuzzlePanel`; `tk.Tk` → `PuzzleApp`; `Exception` → `ImageLoadError` |
| Polymorphism | `t.apply(board)` / `t.undo(board)` on mixed transformation lists (scramble, Undo, Solve); `panel.placeholder_text()` |
| Class interaction | `PuzzleApp` → `ImageProcessor` → `Tile`; `PuzzleApp` → `PuzzleBoard` → `Transformation` |
| JPG / PNG / BMP loading, resize with aspect ratio, crop to divide evenly | `ImageProcessor.load()`, `fit_to_grid()` |
| 3×3 (default), 4×4, 5×5 grid | Grid combobox |
| ≥3 random transformation types, all generated at once, count scales 6/12/20, no tile targeted twice | `PuzzleBoard.scramble()` |
| Reassembly and overlays (faint grid, selection border, green ticks, blue circles) | `ImageProcessor.assemble()` and the `draw_*` methods |
| Error handling | Cancelled dialog, non-image or corrupt files, images too small, clicks outside the image, clicks after finishing, plus a global Tk error handler. Errors are shown in message boxes. |

### Extra features (for D/HD)

- **Difficulty levels:** Easy (4/8/12 transformations), Normal (6/12/20, as in the brief), and Hard (8/15/24).
- **Hard mode** adds a 4th transformation type (colour inversion) and a **time limit** (3, 6 or 10 minutes).
- **Timer and score:** score = 100×tiles − 5×moves − 50×hints − seconds. A best score is kept for each grid and difficulty.
- **Undo** button, built on the polymorphic `undo()`.
- **New Scramble** button.
- Keyboard shortcuts.

## Files and team split

| File | Owner | Contents |
|---|---|---|
| `image_processor.py` | Prince Nagarkoti| OpenCV loading, resize/crop, split/assemble, overlays |
| `tile.py` | Prince Nagarkoti| `Tile` class |
| `transformations.py` | Prakash Dangi | Abstract `Transformation` and its subclasses |
| `puzzle.py` | Prakash Dangi | `PuzzleBoard`, difficulty levels, scramble/hint/solve. Run `python puzzle.py` for a self-test. |
| `gui.py` | Kritika GC| Tkinter window, panels, event handling, timer |
| `main.py` | Kritika GC | Entry point |

## Team

- Member 1: Prince Nagarkoti/ S398427
- Member 2: Prakash Dangi / S406258
- Member 3: Kritika GC / S399271
