import numpy as np

from model.hsc import HSC
from openisp.core.frame import Frame, PixelRange
from openisp.core.pipeline import Pipeline
from openisp.core.stage import PipelineContext
from openisp.core.types import CfaPattern, PixelDomain
from openisp.stages.legacy import (
    AutoWhiteBalanceEstimatorStage,
    ColorSpaceConversionStage,
    GammaStage,
    WhiteBalanceGainStage,
)


def test_awb_estimation_is_separate_from_gain_application():
    data = np.array([[100, 200], [200, 50]], dtype=np.uint16)
    frame = Frame(data, PixelDomain.BAYER, PixelRange(0, 1023, 10), CfaPattern.RGGB)
    context = PipelineContext()
    estimated = AutoWhiteBalanceEstimatorStage.from_config({}).process(frame, context)
    np.testing.assert_array_equal(estimated.data, data)
    assert estimated.artifacts["awb-gains"]["red"] == 2.0
    assert estimated.artifacts["awb-gains"]["blue"] == 4.0

    application = WhiteBalanceGainStage.from_config({"use_estimated": True})
    balanced = application.process(estimated, context)
    assert balanced.data[0, 0] == 200
    assert balanced.data[1, 1] == 200


def test_gamma_output_is_the_color_space_conversion_input():
    rgb = np.array([[[16, 64, 144], [25, 100, 225]]], dtype=np.uint8)
    frame = Frame(rgb, PixelDomain.RGB_LINEAR, PixelRange(0, 255, 8))
    gamma = GammaStage.from_config({"gamma": 0.5, "bit_depth": 8})
    conversion = ColorSpaceConversionStage.from_config(
        {"matrix": [[1024, 0, 0, 0], [0, 1024, 0, 0], [0, 0, 1024, 0]]}
    )
    result = Pipeline([gamma, conversion]).run(frame)
    gamma_only = gamma.process(frame, PipelineContext())
    np.testing.assert_array_equal(result.frame.data, gamma_only.data.astype(np.uint8))
    assert not np.array_equal(result.frame.data, rgb)


def test_hue_rotation_is_not_overwritten_by_saturation():
    chroma = np.array([[[200, 128]]], dtype=np.uint8)
    rotated = HSC(chroma, hue=90, saturation=256, clip=255).execute()
    np.testing.assert_allclose(rotated, [[[128, 56]]], atol=1.0)
