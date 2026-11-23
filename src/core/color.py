import numpy as np


def rgb_to_gray(rgb_u8) -> np.ndarray:
    """Apply the specified luminance weights with half-up rounding."""
    red, green, blue = np.moveaxis(np.asarray(rgb_u8, dtype=np.int32), -1, 0)
    return ((299 * red + 587 * green + 114 * blue + 500) // 1000).astype(np.uint8)


def rgb_to_hsv(rgb_u8) -> np.ndarray:
    """Convert RGB to HSV with 256 hue bins and byte-valued saturation and value."""
    rgb = np.asarray(rgb_u8, dtype=np.int32)
    red, green, blue = np.moveaxis(rgb, -1, 0)
    value = rgb.max(axis=-1)
    chroma = value - rgb.min(axis=-1)

    # Express the hue in sixths of a turn with chroma as the denominator.
    hue_numerator = np.select(
        [red == value, green == value],
        [green - blue, blue - red + 2 * chroma],
        default=red - green + 4 * chroma,
    )
    turn = 6 * np.maximum(chroma, 1)
    hue = (hue_numerator % turn) * 256 // turn
    saturation = (2 * 255 * chroma + value) // (2 * np.maximum(value, 1))
    return np.stack((hue, saturation, value), axis=-1).astype(np.uint8)


def grid_cells(h, w, g) -> list[tuple[int, int, int, int]]:
    """Return row-major cells with exclusive bottom and right edges."""
    if g <= 0:
        raise ValueError("g must be positive")

    row_edges = [i * h // g for i in range(g + 1)]
    col_edges = [i * w // g for i in range(g + 1)]
    return [
        (row_edges[row], row_edges[row + 1], col_edges[col], col_edges[col + 1])
        for row in range(g)
        for col in range(g)
    ]
