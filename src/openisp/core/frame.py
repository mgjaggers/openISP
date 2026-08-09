"""Typed frame and per-frame metadata containers."""

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Mapping, Optional

import numpy as np

from openisp.core.types import CfaPattern, PixelDomain


@dataclass(frozen=True)
class PixelRange:
    """Declared numerical range for an image plane or interleaved image."""

    minimum: float
    maximum: float
    bit_depth: Optional[int] = None
    normalized: bool = False

    def __post_init__(self) -> None:
        if self.maximum <= self.minimum:
            raise ValueError("pixel-range maximum must exceed minimum")
        if self.bit_depth is not None and self.bit_depth <= 0:
            raise ValueError("bit depth must be positive")


@dataclass(frozen=True)
class FrameMetadata:
    """Metadata that must travel with a frame through the pipeline."""

    frame_id: int = 0
    sensor_id: Optional[str] = None
    lens_id: Optional[str] = None
    timestamp_ns: Optional[int] = None
    exposure_time_s: Optional[float] = None
    analog_gain: Optional[float] = None
    digital_gain: Optional[float] = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def with_extra(self, key: str, value: Any) -> "FrameMetadata":
        extras = dict(self.extras)
        extras[key] = value
        return replace(self, extras=extras)


@dataclass(frozen=True)
class Frame:
    """An image plus the declarations needed to process it safely."""

    data: np.ndarray
    domain: PixelDomain
    pixel_range: PixelRange
    cfa: Optional[CfaPattern] = None
    metadata: FrameMetadata = field(default_factory=FrameMetadata)
    artifacts: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.data, np.ndarray):
            raise TypeError("frame data must be a numpy.ndarray")
        if self.data.ndim not in (2, 3):
            raise ValueError("frame data must be a 2-D plane or 3-D image")
        if self.domain == PixelDomain.BAYER:
            if self.data.ndim != 2:
                raise ValueError("Bayer frames must be two-dimensional")
            if self.cfa is None:
                raise ValueError("Bayer frames require a CFA pattern")
        if self.domain in (PixelDomain.RGB_LINEAR, PixelDomain.RGB_ENCODED, PixelDomain.YUV):
            if self.data.ndim != 3 or self.data.shape[2] != 3:
                raise ValueError("RGB and YUV frames must have three channels")

    def evolve(
        self,
        *,
        data: Optional[np.ndarray] = None,
        domain: Optional[PixelDomain] = None,
        pixel_range: Optional[PixelRange] = None,
        cfa: object = ...,
        metadata: Optional[FrameMetadata] = None,
        artifacts: Optional[Mapping[str, Any]] = None,
    ) -> "Frame":
        next_cfa = self.cfa if cfa is ... else cfa
        return Frame(
            data=self.data if data is None else data,
            domain=self.domain if domain is None else domain,
            pixel_range=self.pixel_range if pixel_range is None else pixel_range,
            cfa=next_cfa,  # type: ignore[arg-type]
            metadata=self.metadata if metadata is None else metadata,
            artifacts=self.artifacts if artifacts is None else artifacts,
        )

    def with_artifact(self, key: str, value: Any) -> "Frame":
        artifacts: Dict[str, Any] = dict(self.artifacts)
        artifacts[key] = value
        return self.evolve(artifacts=artifacts)
