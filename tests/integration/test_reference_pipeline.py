from pathlib import Path

import numpy as np

from openisp.core.config import PipelineConfig
from openisp.core.frame import Frame, PixelRange
from openisp.core.pipeline import Pipeline
from openisp.core.registry import registry
from openisp.core.types import PixelDomain
from openisp.stages.legacy import BilateralDenoiseStage, NonLocalMeansStage


def test_registered_reference_configuration_is_domain_valid():
    config = PipelineConfig.load(Path("config/pipeline.json"))
    pipeline = Pipeline.from_config(config)
    assert pipeline.validate(PixelDomain.BAYER) == PixelDomain.YUV
    assert len(pipeline.stages) == 16
    assert len(tuple(registry.names())) == 16


def test_reference_pipeline_runs_all_four_bayer_patterns(bayer_frame):
    config = PipelineConfig.load(Path("config/pipeline.json"))
    result = Pipeline.from_config(config).run(bayer_frame)
    assert result.frame.domain == PixelDomain.YUV
    assert result.frame.data.shape == bayer_frame.data.shape + (3,)
    assert result.frame.data.dtype == np.uint8
    assert set(result.bypassed_stages) == {"non-local-means", "bilateral-denoise"}
    assert "edge-map" in result.frame.artifacts
    assert np.isfinite(result.frame.data).all()


def test_optional_legacy_denoisers_are_adapted_to_three_channel_yuv():
    data = np.full((8, 8, 3), 128, dtype=np.uint8)
    data[4, 4, 0] = 200
    frame = Frame(data, PixelDomain.YUV, PixelRange(0, 255, 8))
    nlm = NonLocalMeansStage.from_config(
        {"patch_radius": 1, "search_radius": 2, "strength": 15, "clip": 255}
    )
    bilateral = BilateralDenoiseStage.from_config({})
    result = Pipeline([nlm, bilateral]).run(frame)
    assert result.frame.data.shape == data.shape
    np.testing.assert_array_equal(result.frame.data[:, :, 1:3], data[:, :, 1:3])
