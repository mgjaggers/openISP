import time
import tracemalloc
from pathlib import Path

import pytest

from openisp.core.config import PipelineConfig
from openisp.core.pipeline import Pipeline


@pytest.mark.performance
def test_small_reference_workload_has_a_bounded_runtime_and_peak_memory(bayer_frame):
    config = PipelineConfig.load(Path("config/pipeline.json"))
    pipeline = Pipeline.from_config(config)
    tracemalloc.start()
    started = time.perf_counter()
    pipeline.run(bayer_frame)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert elapsed < 10.0
    assert peak < 128 * 1024 * 1024
