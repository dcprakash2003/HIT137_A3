"""
image_processor.py
Owner: Prince Nagarkoti (Image processing & tiles)

All the OpenCV work is in here:
- loading JPG / PNG / BMP files
- resizing and cropping so the grid divides evenly
- splitting into tiles and putting them back together
- drawing the grid, selection border, green ticks and blue hint circles

OOP stuff used here:
- custom exception (ImageLoadError inherits from Exception)
- encapsulation (colours and sizes are private)
- class interaction (gui.py uses ImageProcessor, which creates Tile objects)
"""

import os

import cv2
import numpy as np

from tile import Tile


class ImageLoadError(Exception):
    """Raised when a file can't be used as a puzzle image.

    The GUI catches it and shows the message in a message box.
    """


class ImageProcessor:
    """Loads images and draws everything the player sees."""

    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
    MIN_TILE_SIZE = 20          # smallest tile (in pixels) we accept

    def __init__(self, display_size: int = 450):
        self._display_size = display_size
        # OpenCV uses BGR, not RGB
        self._grid_colour = (255, 255, 255)
        self._grid_alpha = 0.35
        self._select_colour = (0, 215, 255)     # yellow/orange
        self._tick_colour = (0, 200, 0)         # green
        self._hint_colour = (255, 80, 0)        # blue

    @property
    def display_size(self) -> int:
        return self._display_size

    # loading
    def load(self, path: str) -> np.ndarray:
        """Read an image file and return it as a BGR array.

        Raises ImageLoadError with a readable message if anything goes wrong.
        """
        if not path or not os.path.isfile(path):
            raise ImageLoadError("The selected file does not exist.")

        ext = os.path.splitext(path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ImageLoadError(
                f"'{os.path.basename(path)}' is not a supported image.\n"
                "Please choose a JPG, PNG or BMP file.")

        # fromfile + imdecode instead of imread because imread can fail on
        # Windows paths with spaces or odd characters
        try:
            data = np.fromfile(path, dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        except (OSError, cv2.error) as exc:
            raise ImageLoadError(f"Could not read the file:\n{exc}") from exc

        if image is None:
            raise ImageLoadError(
                f"'{os.path.basename(path)}' could not be decoded.\n"
                "The file may be damaged or is not really an image.")

        return self._to_bgr(image)

    @staticmethod
    def _to_bgr(image: np.ndarray) -> np.ndarray:
        """Turn greyscale, transparent or 16-bit images into 8-bit BGR."""
        if image.dtype != np.uint8:                       # 16-bit PNG etc.
            image = cv2.normalize(image, None, 0, 255,
                                  cv2.NORM_MINMAX).astype(np.uint8)
        if image.ndim == 2:                               # greyscale
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:                           # has alpha
            # transparent parts go on a white background
            bgr = image[:, :, :3].astype(np.float32)
            alpha = image[:, :, 3:4].astype(np.float32) / 255.0
            white = np.full_like(bgr, 255.0)
            return (bgr * alpha + white * (1 - alpha)).astype(np.uint8)
        return image

    def fit_to_grid(self, image: np.ndarray, grid: int) -> np.ndarray:
        """Resize keeping the aspect ratio, then centre-crop to a square
        whose side divides evenly by grid.

        Tiles have to be square so rotating them doesn't change their shape.
        """
        h, w = image.shape[:2]
        if min(h, w) < grid * self.MIN_TILE_SIZE:
            raise ImageLoadError(
                f"The image is too small ({w}x{h}) for a {grid}x{grid} grid.\n"
                f"Please use an image at least "
                f"{grid * self.MIN_TILE_SIZE} pixels on its shorter side.")

        # side length the grid divides evenly (e.g. 448 for a 4x4)
        side = (self._display_size // grid) * grid

        # resize so the short side equals side
        scale = side / min(h, w)
        new_w = max(side, round(w * scale))
        new_h = max(side, round(h * scale))
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        resized = cv2.resize(image, (new_w, new_h), interpolation=interp)

        # crop the long side down to side x side
        top = (new_h - side) // 2
        left = (new_w - side) // 2
        return resized[top:top + side, left:left + side].copy()

    # splitting and joining
    @staticmethod
    def split(image: np.ndarray, grid: int) -> list:
        """Cut a square image into grid*grid Tile objects, row by row."""
        tile_size = image.shape[0] // grid
        tiles = []
        for row in range(grid):
            for col in range(grid):
                y, x = row * tile_size, col * tile_size
                piece = image[y:y + tile_size, x:x + tile_size]
                tiles.append(Tile(piece, home_index=row * grid + col))
        return tiles

    @staticmethod
    def assemble(tile_images: list, grid: int) -> np.ndarray:
        """Join a flat list of tile images into one picture."""
        if len(tile_images) != grid * grid:
            raise ValueError("Wrong number of tiles for this grid size.")
        rows = [np.hstack(tile_images[r * grid:(r + 1) * grid])
                for r in range(grid)]
        return np.vstack(rows)

    # overlays (each one returns a new image and leaves the input alone)
    @staticmethod
    def _cell(image: np.ndarray, grid: int, index: int):
        """Return (x, y, size) of the cell at this flat index."""
        size = image.shape[0] // grid
        row, col = divmod(index, grid)
        return col * size, row * size, size

    def draw_grid(self, image: np.ndarray, grid: int) -> np.ndarray:
        """Blend thin white lines over the image so the tile edges show."""
        lines = image.copy()
        side = image.shape[0]
        step = side // grid
        for i in range(1, grid):
            cv2.line(lines, (i * step, 0), (i * step, side - 1),
                     self._grid_colour, 1)
            cv2.line(lines, (0, i * step), (side - 1, i * step),
                     self._grid_colour, 1)
        return cv2.addWeighted(lines, self._grid_alpha,
                               image, 1 - self._grid_alpha, 0)

    def draw_selection(self, image: np.ndarray, grid: int,
                       index: int) -> np.ndarray:
        """Draw a border around the selected tile."""
        out = image.copy()
        x, y, size = self._cell(out, grid, index)
        thickness = max(3, size // 25)
        half = thickness // 2
        cv2.rectangle(out, (x + half, y + half),
                      (x + size - 1 - half, y + size - 1 - half),
                      self._select_colour, thickness)
        return out

    def draw_tick(self, image: np.ndarray, grid: int,
                  index: int) -> np.ndarray:
        """Draw a small green tick in the top-right corner of a tile."""
        out = image.copy()
        x, y, size = self._cell(out, grid, index)
        s = max(12, size // 5)                      # size of the tick box
        ox, oy = x + size - s - 4, y + 4            # top-right corner
        # white circle behind it so it shows on any picture
        cv2.circle(out, (ox + s // 2, oy + s // 2), s // 2 + 2,
                   (255, 255, 255), -1, cv2.LINE_AA)
        points = np.array([[ox + s * 0.18, oy + s * 0.52],
                           [ox + s * 0.42, oy + s * 0.76],
                           [ox + s * 0.84, oy + s * 0.26]], dtype=np.int32)
        cv2.polylines(out, [points], False, self._tick_colour,
                      max(2, s // 6), cv2.LINE_AA)
        return out

    def draw_circle(self, image: np.ndarray, grid: int,
                    index: int) -> np.ndarray:
        """Draw a blue hint circle in the middle of a tile."""
        out = image.copy()
        x, y, size = self._cell(out, grid, index)
        centre = (x + size // 2, y + size // 2)
        radius = int(size * 0.38)
        cv2.circle(out, centre, radius, (255, 255, 255),
                   max(4, size // 14), cv2.LINE_AA)        # white outline
        cv2.circle(out, centre, radius, self._hint_colour,
                   max(2, size // 22), cv2.LINE_AA)         # blue ring
        return out

    @staticmethod
    def to_rgb(image: np.ndarray) -> np.ndarray:
        """OpenCV is BGR but Tkinter/PIL want RGB."""
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
