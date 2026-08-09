"""Core frame, stage, registry, configuration and pipeline contracts."""

from openisp.core.config import PipelineConfig, StageSpec
from openisp.core.frame import Frame, FrameMetadata, PixelRange
from openisp.core.pipeline import Pipeline, PipelineResult
from openisp.core.stage import PipelineContext, Stage
from openisp.core.types import CfaPattern, PixelDomain

__all__ = [
    "CfaPattern",
    "Frame",
    "FrameMetadata",
    "Pipeline",
    "PipelineConfig",
    "PipelineContext",
    "PipelineResult",
    "PixelDomain",
    "PixelRange",
    "Stage",
    "StageSpec",
]
