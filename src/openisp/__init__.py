"""Modular Python reference image signal processor."""

from openisp.core.frame import Frame, FrameMetadata, PixelRange
from openisp.core.pipeline import Pipeline, PipelineResult
from openisp.core.types import CfaPattern, PixelDomain
from openisp import stages as _builtin_stages  # noqa: F401

__all__ = [
    "CfaPattern",
    "Frame",
    "FrameMetadata",
    "Pipeline",
    "PipelineResult",
    "PixelDomain",
    "PixelRange",
]

__version__ = "0.1.0"
