from unittest.mock import Mock

import numpy as np
import pytest

from src.core import security_demos


def test_reuse_key_slide_scalar_vector():
    message1 = np.array(0b01001000, dtype=np.uint8)
    # The second message follows from the slide's M1 xor M2 value.
    message2 = message1 ^ np.uint8(0b00100001)
    rng = Mock(spec=np.random.Generator)
    rng.integers.return_value = np.array(0b10110101, dtype=np.uint8)

    result = security_demos.reuse_key_attack(message1, message2, rng)

    assert rng.integers.call_count == 1
    assert int(result["key"]) == 0b10110101
    assert int(result["c1"]) == 0b11111101
    assert int(result["c1_xor_c2"]) == int(result["i1_xor_i2"]) == 0b00100001
    np.testing.assert_array_equal(result["recovered_key"], result["key"])


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
def test_reuse_key_demo_matches_the_array_xor_identity(dtype):
    rng = np.random.default_rng(42)
    limit = int(np.iinfo(dtype).max)
    images = rng.integers(0, limit + 1, size=(2, 4, 5), dtype=dtype)
    original = images.copy()

    result = security_demos.reuse_key_attack(*images, rng)

    assert all(value.dtype == dtype and value.shape == (4, 5) for value in result.values())
    np.testing.assert_array_equal(result["c1"], original[0] ^ result["key"])
    np.testing.assert_array_equal(result["c2"], original[1] ^ result["key"])
    np.testing.assert_array_equal(result["c1_xor_c2"], original[0] ^ original[1])
    np.testing.assert_array_equal(result["i1_xor_i2"], result["c1_xor_c2"])
    np.testing.assert_array_equal(result["recovered_key"], result["key"])
    np.testing.assert_array_equal(images, original)


@pytest.mark.parametrize("failed", [0, 1, 2])
def test_raid5_slide_parity_and_recovery_for_every_disk(failed):
    disks = [np.array(value, dtype=np.uint8) for value in (0b1010, 0b0111, 0b1100)]
    parity = security_demos.raid5_parity(disks)
    damaged = disks.copy()
    damaged[failed] = None

    recovered = security_demos.raid5_recover(damaged, parity, failed)

    assert int(parity) == 0b0001
    assert int(recovered) == int(disks[failed])
    assert recovered.dtype == np.uint8
    assert damaged[failed] is None


def test_raid5_recovers_uint16_blocks_with_a_corrupted_disk():
    disks = np.array([[0, 65535, 256], [32768, 0, 128], [7, 128, 4096]], dtype=np.uint16)
    parity = security_demos.raid5_parity(disks)
    damaged = disks.copy()
    damaged[1] = 42

    recovered = security_demos.raid5_recover(damaged, parity, 1)

    assert recovered.dtype == np.uint16
    np.testing.assert_array_equal(recovered, disks[1])
    np.testing.assert_array_equal(damaged[1], [42, 42, 42])
