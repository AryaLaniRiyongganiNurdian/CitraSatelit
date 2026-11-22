from itertools import product
from unittest.mock import Mock

import numpy as np
import pytest

from src.core import secret_sharing as sharing
from src.core.probability import chi2_sf, chi2_uniform_stat, pearson_r
from src.core.stats import histogram_counts


@pytest.mark.parametrize("secret,pads,last", [
    (150, (100,), 242),
    (173, (60,), 145),
    (100, (25, 77), 48),
])
def test_slide_xor_vectors(secret, pads, last):
    source = np.array(secret, dtype=np.uint8)
    rng = Mock(spec=np.random.Generator)
    rng.integers.side_effect = [np.array(pad, dtype=np.uint8) for pad in pads]

    shares = sharing.split_xor(source, len(pads) + 1, rng)

    assert [share.item() for share in shares] == [*pads, last]
    assert rng.integers.call_count == len(pads)
    np.testing.assert_array_equal(sharing.reconstruct_xor(shares), source)


@pytest.mark.parametrize("secret,pad", list(product((0, 1), repeat=2)))
def test_xor_truth_table(secret, pad):
    rng = Mock(spec=np.random.Generator)
    rng.integers.return_value = np.array(pad, dtype=np.uint8)
    source = np.array(secret, dtype=np.uint8)

    random_share, final_share = sharing.split_xor(source, 2, rng)

    assert int(final_share) == (secret ^ pad)
    assert int(sharing.reconstruct_xor([random_share, final_share])) == secret


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("n", range(2, 9))
@pytest.mark.parametrize("shape", [(4, 5), (4, 5, 3), (4, 5, 13)])
def test_reconstruction_is_bit_exact(dtype, n, shape):
    limit = int(np.iinfo(dtype).max)
    rng = np.random.default_rng(42)
    source = rng.integers(0, limit + 1, size=shape, dtype=dtype)
    source.flat[0], source.flat[-1] = 0, limit
    original = source.copy()

    shares = sharing.split_xor(source, n, rng)
    recovered = sharing.reconstruct_xor(shares[::-1])

    assert isinstance(shares, list)
    assert len(shares) == n
    assert all(share.dtype == dtype and share.shape == shape for share in shares)
    assert recovered.dtype == dtype
    np.testing.assert_array_equal(recovered, original)
    np.testing.assert_array_equal(source, original)
    assert sharing.mse(source, recovered) == 0
    assert sharing.psnr(source, recovered, limit) == float("inf")


def test_metrics_widen_unsigned_samples_and_compute_finite_psnr():
    source = np.array([0, 65535], dtype=np.uint16)
    reversed_source = source[::-1]
    zeros = np.zeros_like(source)

    assert sharing.mse(source, reversed_source) == 65535 ** 2
    assert sharing.psnr(source, reversed_source, 65535) == pytest.approx(0, abs=1e-12)
    assert sharing.psnr(source, zeros, 65535) == pytest.approx(3.01029995664, abs=1e-10)


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("seed", range(42, 62))
def test_random_shares_pass_uniformity_check_for_twenty_seeds(dtype, seed):
    source = np.zeros((128, 128), dtype=dtype)
    shares = sharing.split_xor(source, 3, np.random.default_rng(seed))

    for share in shares[:-1]:
        byte_values = share >> 8 if dtype == np.uint16 else share
        counts = histogram_counts(byte_values, 256)
        assert chi2_sf(chi2_uniform_stat(counts), 255) > 0.001


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("n", (2, 3, 8))
def test_every_n_minus_one_subset_is_dissimilar_to_source(dtype, n):
    limit = int(np.iinfo(dtype).max)
    source = np.linspace(0, limit, 128 ** 2, dtype=dtype).reshape(128, 128)
    shares = sharing.split_xor(source, n, np.random.default_rng(42))

    for missing_index in range(n):
        partial = sharing.reconstruct_xor(shares[:missing_index] + shares[missing_index + 1:])
        assert sharing.mse(source, partial) > limit ** 2 / 10
        assert abs(pearson_r(source, partial)) < 0.05


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("p", [0.0, 1.0])
def test_flip_bits_probability_endpoints(dtype, p):
    limit = int(np.iinfo(dtype).max)
    source = np.array([[0, 7, 13, limit]], dtype=dtype)
    original = source.copy()

    with np.errstate(all="raise"):
        flipped = sharing.flip_bits(source, p, np.random.default_rng(42), bits=np.iinfo(dtype).bits)

    assert flipped.dtype == dtype
    np.testing.assert_array_equal(source, original)
    np.testing.assert_array_equal(flipped, original if p == 0 else np.bitwise_not(original))


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("corrupted", [1, 2])
def test_corrupted_shares_match_binomial_pixel_and_bit_error_rates(dtype, corrupted):
    rng = np.random.default_rng(42)
    bits = np.iinfo(dtype).bits
    size = 256 * 512
    source = rng.integers(0, 1 << bits, size=(256, 512), dtype=dtype)
    shares = sharing.split_xor(source, 3, rng)
    p = 0.01

    for i in range(corrupted):
        shares[i] = sharing.flip_bits(shares[i], p, rng, bits)

    delta = sharing.reconstruct_xor(shares) ^ source
    p_eff = p if corrupted == 1 else (1 - (1 - 2 * p) ** corrupted) / 2
    expected_pixels = 1 - (1 - p_eff) ** bits
    observed_pixels = np.count_nonzero(delta) / size
    assert abs(observed_pixels - expected_pixels) <= 3 * np.sqrt(
        expected_pixels * (1 - expected_pixels) / size
    )

    observed_msb = np.count_nonzero(delta & (1 << (bits - 1))) / size
    assert abs(observed_msb - p_eff) <= 3 * np.sqrt(p_eff * (1 - p_eff) / size)


@pytest.mark.parametrize("dtype,bit", [(np.uint8, 7), (np.uint16, 15)])
def test_tampering_one_share_pixel_changes_exactly_one_reconstructed_pixel(dtype, bit):
    source = np.arange(36, dtype=dtype).reshape(4, 9)
    shares = sharing.split_xor(source, 3, np.random.default_rng(42))
    first = shares[0].copy()
    x, y = 7, 2

    tampered = sharing.tamper_pixel(shares[0], x, y, bit=bit)
    reconstructed = sharing.reconstruct_xor([tampered, *shares[1:]])

    np.testing.assert_array_equal(shares[0], first)
    assert reconstructed.dtype == dtype
    np.testing.assert_array_equal(np.argwhere(reconstructed != source), [[y, x]])
    assert abs(int(reconstructed[y, x]) - int(source[y, x])) == 1 << bit



@pytest.mark.parametrize("dtype,msb", [(np.uint8, 128), (np.uint16, 32768)])
def test_tamper_pixel_defaults_to_most_significant_bit(dtype, msb):
    source = np.array([[1, 2, 3], [4, 5, msb]], dtype=dtype)
    original = source.copy()
    expected = original.copy()
    expected[1, 2] = 0

    tampered = sharing.tamper_pixel(source, x=2, y=1)

    assert tampered.dtype == dtype
    np.testing.assert_array_equal(tampered, expected)
    np.testing.assert_array_equal(source, original)


@pytest.mark.parametrize("dtype,channels", [(np.uint8, 3), (np.uint16, 13)])
@pytest.mark.parametrize("channel", [None, np.int64(2)])
def test_tamper_pixel_applies_to_all_channels_or_one_valid_channel(dtype, channels, channel):
    source = np.arange(2 * 4 * channels, dtype=dtype).reshape(2, 4, channels)
    original = source.copy()
    expected = original.copy()
    selected = slice(None) if channel is None else channel
    expected[0, 3, selected] ^= 1 << 2

    tampered = sharing.tamper_pixel(source, x=3, y=0, bit=2, channel=channel)

    assert tampered.dtype == dtype
    np.testing.assert_array_equal(tampered, expected)
    np.testing.assert_array_equal(source, original)


@pytest.mark.parametrize("x,y", [(-1, 0), (3, 0), (0, -1), (0, 2)])
def test_tamper_pixel_and_block_reject_out_of_bounds_coordinates(x, y):
    source = np.zeros((2, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        sharing.tamper_pixel(source, x, y)
    with pytest.raises(ValueError):
        sharing.tamper_block(source, x, y, 1, np.random.default_rng(42))


@pytest.mark.parametrize("dtype,invalid_bit", [
    (np.uint8, -1), (np.uint8, 8), (np.uint16, -1), (np.uint16, 16),
])
def test_tamper_pixel_rejects_bits_outside_dtype_width(dtype, invalid_bit):
    with pytest.raises(ValueError):
        sharing.tamper_pixel(np.zeros((2, 3), dtype=dtype), 0, 0, bit=invalid_bit)


@pytest.mark.parametrize("dtype,channels", [(np.uint8, 3), (np.uint16, 13)])
@pytest.mark.parametrize("channel", [-1, 13, 1.5])
def test_tamper_pixel_rejects_invalid_channel(dtype, channels, channel):
    source = np.zeros((2, 3, channels), dtype=dtype)
    with pytest.raises(ValueError):
        sharing.tamper_pixel(source, 0, 0, channel=channel)


@pytest.mark.parametrize("size", [0, -1])
def test_tamper_block_rejects_nonpositive_size(size):
    source = np.zeros((4, 6), dtype=np.uint8)
    with pytest.raises(ValueError):
        sharing.tamper_block(source, 0, 0, size, np.random.default_rng(42))


@pytest.mark.parametrize("dtype,shape", [
    (np.uint8, (4, 6)), (np.uint8, (4, 6, 3)), (np.uint16, (4, 6, 13)),
])
@pytest.mark.parametrize("x,y,size,x_end,y_end", [
    (0, 0, 1, 1, 1),
    (1, 0, 2, 3, 2),
    (5, 0, 3, 6, 3),
    (1, 3, 3, 4, 4),
    (4, 2, 5, 6, 4),
])
def test_tamper_block_clips_at_edges_and_xors_every_element(dtype, shape, x, y, size, x_end, y_end):
    source = np.arange(np.prod(shape), dtype=dtype).reshape(shape)
    original = source.copy()
    expected = original.copy()
    block = expected[y:y_end, x:x_end]
    limit = 1 << np.iinfo(dtype).bits
    block ^= np.random.default_rng(42).integers(1, limit, size=block.shape, dtype=dtype)
    changed = np.zeros(shape, dtype=bool)
    changed[y:y_end, x:x_end] = True

    tampered = sharing.tamper_block(source, x, y, size, np.random.default_rng(42))

    assert tampered.dtype == dtype
    np.testing.assert_array_equal(tampered, expected)
    np.testing.assert_array_equal(tampered != original, changed)
    np.testing.assert_array_equal(source, original)
