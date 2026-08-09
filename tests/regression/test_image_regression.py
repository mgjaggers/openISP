import hashlib
from pathlib import Path

import pytest

from openisp.core.config import PipelineConfig
from openisp.core.pipeline import Pipeline


@pytest.mark.regression
def test_synthetic_reference_image_digest(bayer_frame):
    """Pin the complete reference path for every Bayer layout."""

    config = PipelineConfig.load(Path("config/pipeline.json"))
    output = Pipeline.from_config(config).run(bayer_frame).frame.data
    digest = hashlib.sha256(output.tobytes(order="C")).hexdigest()
    expected = {
        "rggb": "af3b85810cec99fa3374a03bcebd8f56e74b567141ce98b1faa207cfbb1d02a1",
        "bggr": "08569ffdc746f15931dec68fae4ec16154c13693f0aafaa1fb31ff2336fae3ff",
        "gbrg": "9b25671730c8d08d725fba03427b16f2736face924938201677a55d7cbac666a",
        "grbg": "75e321fa2e38b5540257ac116a99a460373f31e4ae1fd9e3b3d74f7be47d4c4d",
    }
    assert digest == expected[bayer_frame.cfa.value]
