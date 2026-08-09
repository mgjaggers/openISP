import numpy as np
import pytest

from openisp.core.config import PipelineConfig
from openisp.core.frame import Frame, PixelRange
from openisp.core.numeric import NumericPolicy, RoundingMode, safe_working_copy
from openisp.core.pipeline import Pipeline
from openisp.core.stage import PipelineContext, Stage
from openisp.core.types import CfaPattern, PixelDomain


class AddOne(Stage):
    name = "add-one"
    input_domains = (PixelDomain.LUMA,)
    output_domain = PixelDomain.LUMA

    def process(self, frame, context):
        return frame.evolve(data=frame.data + 1)


class NeedsAddOne(Stage):
    name = "needs-add-one"
    input_domains = (PixelDomain.LUMA,)
    output_domain = PixelDomain.LUMA
    requires = frozenset({"add-one"})

    def process(self, frame, context):
        return frame


def test_frame_requires_cfa_for_bayer():
    with pytest.raises(ValueError, match="CFA"):
        Frame(np.zeros((2, 2)), PixelDomain.BAYER, PixelRange(0, 1))


def test_all_cfa_patterns_partition_an_even_frame():
    for pattern in CfaPattern:
        covered = np.zeros((8, 10), dtype=np.uint8)
        for index in pattern.slices().values():
            covered[index] += 1
        np.testing.assert_array_equal(covered, np.ones_like(covered))


def test_numeric_policy_promotes_rounds_and_saturates():
    values = np.array([-1.0, 0.5, 1.5, 255.9, 300.0])
    policy = NumericPolicy(0, 255, "uint8", RoundingMode.NEAREST_EVEN)
    np.testing.assert_array_equal(policy.apply(values), [0, 0, 2, 255, 255])
    unsigned = np.array([0, 1], dtype=np.uint16)
    promoted = safe_working_copy(unsigned)
    assert promoted.dtype == np.int64
    assert int(promoted[0] - promoted[1]) == -1


def test_pipeline_bypass_is_identity_and_recorded():
    frame = Frame(np.zeros((2, 2)), PixelDomain.LUMA, PixelRange(0, 255, 8))
    result = Pipeline([AddOne(enabled=False)]).run(frame)
    assert result.frame is frame
    assert result.executed_stages == ()
    assert result.bypassed_stages == ("add-one",)


def test_pipeline_rejects_unmet_dependency_and_wrong_domain():
    with pytest.raises(ValueError, match="unmet dependencies"):
        Pipeline([NeedsAddOne()]).validate(PixelDomain.LUMA)
    with pytest.raises(ValueError, match="accepts"):
        Pipeline([AddOne()]).validate(PixelDomain.BAYER)


def test_pipeline_exports_intermediate_metadata(tmp_path):
    frame = Frame(np.zeros((2, 2)), PixelDomain.LUMA, PixelRange(0, 255, 8))
    result = Pipeline([AddOne()], export_directory=tmp_path).run(frame, PipelineContext())
    np.testing.assert_array_equal(result.frame.data, np.ones((2, 2)))
    assert (tmp_path / "000_add-one.npy").exists()
    assert (tmp_path / "000_add-one.json").exists()


def test_configuration_snapshot_is_stable(tmp_path):
    config = PipelineConfig.from_dict(
        {"schema_version": 1, "profile": "test", "stages": [{"name": "one", "enabled": False}]}
    )
    first = config.digest()
    output = tmp_path / "snapshot.json"
    config.write_snapshot(output)
    assert first in output.read_text(encoding="utf-8")
    assert config.digest() == first
