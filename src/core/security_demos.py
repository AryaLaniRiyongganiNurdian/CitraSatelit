import numpy as np

from src.core.secret_sharing import reconstruct_xor, split_xor


def reuse_key_attack(i1, i2, rng) -> dict[str, np.ndarray]:
    """Demonstrate the XOR identity for two arrays encrypted with one pad."""
    first, second = np.asarray(i1), np.asarray(i2)
    if first.shape != second.shape or first.dtype != second.dtype:
        raise ValueError("inputs must have the same shape and dtype")

    key, c1 = split_xor(first, 2, rng)
    c2 = np.asarray(np.bitwise_xor(second, key))
    return {
        "key": key,
        "c1": c1,
        "c2": c2,
        "c1_xor_c2": np.asarray(np.bitwise_xor(c1, c2)),
        "i1_xor_i2": np.asarray(np.bitwise_xor(first, second)),
        "recovered_key": np.asarray(np.bitwise_xor(c1, first)),
    }


def raid5_parity(disks) -> np.ndarray:
    """Return the shared XOR parity block."""
    return reconstruct_xor(disks)


def raid5_recover(disks, parity, failed) -> np.ndarray:
    """Recover one failed data block from the parity and surviving blocks."""
    if not 0 <= failed < len(disks):
        raise ValueError("failed must be an index in disks")

    surviving = (disk for index, disk in enumerate(disks) if index != failed)
    return reconstruct_xor((parity, *surviving))
