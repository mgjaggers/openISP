import numpy as np
import pytest

from model.aaf import AAF
from model.awb import WBGC
from model.blc import BLC
from model.cfa import CFA
from model.cnf import CNF
from model.dpc import DPC
from openisp.core.types import CfaPattern


def patterned_image(pattern, height=8, width=8):
    image = np.empty((height, width), dtype=np.uint16)
    values = {"r": 100, "gr": 200, "gb": 300, "b": 400}
    for color, index in pattern.slices().items():
        image[index] = values[color]
    return image


@pytest.mark.parametrize("pattern", list(CfaPattern))
def test_black_level_and_white_balance_address_correct_cfa_planes(pattern):
    image = patterned_image(pattern)
    offsets = [1, 2, 3, 4, 0, 0]
    corrected = BLC(image.copy(), offsets, pattern.value, 1023).execute()
    gains = [2, 3, 4, 1]
    balanced = WBGC(image.copy(), gains, pattern.value, 2047).execute()
    expected_offset = {"r": 1, "gr": 2, "gb": 3, "b": 4}
    expected_gain = {"r": 2, "gr": 3, "gb": 4, "b": 1}
    expected_value = {"r": 100, "gr": 200, "gb": 300, "b": 400}
    for color, index in pattern.slices().items():
        assert np.all(corrected[index] == expected_value[color] + expected_offset[color])
        assert np.all(balanced[index] == expected_value[color] * expected_gain[color])


@pytest.mark.parametrize("pattern", list(CfaPattern))
def test_cnf_grbg_and_other_paths_preserve_non_noise_input(pattern):
    image = patterned_image(pattern)
    output = CNF(image.copy(), pattern.value, 65535, [1, 1, 1, 1], 1023).execute()
    np.testing.assert_array_equal(output, image)


@pytest.mark.parametrize("pattern", list(CfaPattern))
def test_demosaic_supports_every_declared_bayer_pattern(pattern):
    output = CFA(patterned_image(pattern), "malvar", pattern.value, 1023).execute()
    assert output.shape == (8, 8, 3)
    assert np.isfinite(output).all()
    assert output.min() >= 0
    assert output.max() <= 1023


def test_pattern_independent_bayer_stages_preserve_shape_and_range():
    image = np.full((8, 8), 64, dtype=np.uint16)
    corrected = DPC(image.copy(), 30, "gradient", 1023).execute()
    filtered = AAF(corrected).execute()
    assert filtered.shape == image.shape
    assert filtered.min() >= 0
    assert filtered.max() <= 1023
