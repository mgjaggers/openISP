"""Shared enumerations and CFA geometry utilities."""

from enum import Enum
from typing import Dict, Tuple


class PixelDomain(str, Enum):
    """Semantic domain of a frame's pixel array."""

    BAYER = "bayer"
    RGB_LINEAR = "rgb-linear"
    RGB_ENCODED = "rgb-encoded"
    YUV = "yuv"
    LUMA = "luma"
    CHROMA = "chroma"


class CfaPattern(str, Enum):
    """Supported 2x2 Bayer patterns."""

    RGGB = "rggb"
    BGGR = "bggr"
    GBRG = "gbrg"
    GRBG = "grbg"

    @property
    def tile(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        return {
            CfaPattern.RGGB: (("r", "gr"), ("gb", "b")),
            CfaPattern.BGGR: (("b", "gb"), ("gr", "r")),
            CfaPattern.GBRG: (("gb", "b"), ("r", "gr")),
            CfaPattern.GRBG: (("gr", "r"), ("b", "gb")),
        }[self]

    def slices(self) -> Dict[str, Tuple[slice, slice]]:
        result = {}
        for row, colors in enumerate(self.tile):
            for column, color in enumerate(colors):
                result[color] = (slice(row, None, 2), slice(column, None, 2))
        return result
