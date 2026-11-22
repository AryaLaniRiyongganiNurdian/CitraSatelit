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


def tamper_pixel(arr, x, y, bit=None) -> np.ndarray:
    """Flip the specified bit at (x, y) in a single-channel share copy."""
    source = _unsigned_array(arr)
    if bit is None or source.ndim == 3:
        raise NotImplementedError("default bit or multichannel pixel policy is pending")
    if source.ndim != 2 or not (0 <= x < source.shape[1] and 0 <= y < source.shape[0]):
        raise ValueError("pixel coordinates must be inside a 2D share")
    if not 0 <= bit < np.iinfo(source.dtype).bits:
        raise ValueError("bit must be within the array dtype's bit width")

    tampered = source.copy()
    tampered[y, x] ^= source.dtype.type(1 << bit)
    return tampered


def tamper_block(arr, x, y, size, rng) -> np.ndarray:
    raise NotImplementedError("block policy is pending; see docs/open-questions.md")
