import numpy as np


def _unsigned_array(arr) -> np.ndarray:
    array = np.asarray(arr)
    if array.dtype not in (np.uint8, np.uint16):
        raise ValueError("expected a uint8 or uint16 array")
    return array


def split_xor(arr, n, rng) -> list[np.ndarray]:
    """Draw n-1 uniform shares and close the XOR with the last share."""
    source = _unsigned_array(arr)
    if n < 2:
        raise ValueError("at least two shares are required")

    levels = int(np.iinfo(source.dtype).max) + 1
    final_share = source.copy()
    shares = []
    for _ in range(n - 1):
        random_share = rng.integers(0, levels, size=source.shape, dtype=source.dtype)
        np.bitwise_xor(final_share, random_share, out=final_share)
        shares.append(random_share)
    shares.append(final_share)
    return shares


def reconstruct_xor(shares) -> np.ndarray:
    """XOR the supplied shares, including a partial set for demonstrations."""
    remaining = iter(shares)
    first = next(remaining, None)
    if first is None:
        raise ValueError("at least one share is required")

    reconstructed = _unsigned_array(first).copy()
    for share in remaining:
        share = _unsigned_array(share)
        if share.shape != reconstructed.shape or share.dtype != reconstructed.dtype:
            raise ValueError("all shares must have the same shape and dtype")
        np.bitwise_xor(reconstructed, share, out=reconstructed)
    return reconstructed


def mse(a, b) -> float:
    left = np.asarray(a, dtype=np.float64)
    right = np.asarray(b, dtype=np.float64)
    if left.shape != right.shape or not left.size:
        raise ValueError("expected nonempty arrays of the same shape")

    return float(np.mean((left - right) ** 2))


def psnr(a, b, max_val) -> float:
    if not max_val > 0:
        raise ValueError("max_val must be positive")

    error = mse(a, b)
    if error == 0:
        return float("inf")
    return float(20 * np.log10(max_val) - 10 * np.log10(error))


def flip_bits(arr, p, rng, bits) -> np.ndarray:
    """Flip each of the specified bits independently with probability p."""
    source = _unsigned_array(arr)
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    if not 1 <= bits <= np.iinfo(source.dtype).bits:
        raise ValueError("bits must be within the array dtype's bit width")

    flipped = source.copy()
    if p == 0:
        return flipped
    if p == 1:
        np.bitwise_xor(flipped, source.dtype.type((1 << bits) - 1), out=flipped)
        return flipped

    for bit in range(bits):
        mask = rng.random(source.shape) < p
        np.bitwise_xor(flipped, source.dtype.type(1 << bit), out=flipped, where=mask)
    return flipped


def _valid_index(value, limit) -> bool:
    return isinstance(value, (int, np.integer)) and 0 <= value < limit


def _tamper_source(arr, x, y) -> np.ndarray:
    source = _unsigned_array(arr)
    if source.ndim not in (2, 3):
        raise ValueError("expected a 2D or 3D share image")

    height, width = source.shape[:2]
    if not (_valid_index(x, width) and _valid_index(y, height)):
        raise ValueError("pixel coordinates must be inside the share image")
    return source


def tamper_pixel(arr, x, y, bit=None, channel=None) -> np.ndarray:
    """Flip one bit at (x, y), using the MSB and all channels by default."""
    source = _tamper_source(arr, x, y)
    bits = np.iinfo(source.dtype).bits
    if bit is None:
        bit = bits - 1
    if not _valid_index(bit, bits):
        raise ValueError("bit must be within the array dtype's bit width")

    pixel = (int(y), int(x))
    if channel is not None:
        if source.ndim != 3 or not _valid_index(channel, source.shape[2]):
            raise ValueError("channel must be an index in a 3D share image")
        pixel += (int(channel),)

    tampered = source.copy()
    tampered[pixel] ^= source.dtype.type(1 << int(bit))
    return tampered


def tamper_block(arr, x, y, size, rng) -> np.ndarray:
    """XOR a clipped block at (x, y) with a nonzero mask per element."""
    source = _tamper_source(arr, x, y)
    if not isinstance(size, (int, np.integer)) or size < 1:
        raise ValueError("size must be a positive integer")

    height, width = source.shape[:2]
    x, y, size = int(x), int(y), int(size)
    x_end, y_end = min(width, x + size), min(height, y + size)
    tampered = source.copy()
    block = tampered[y:y_end, x:x_end]
    levels = 1 << np.iinfo(source.dtype).bits
    block ^= rng.integers(1, levels, size=block.shape, dtype=source.dtype)
    return tampered
