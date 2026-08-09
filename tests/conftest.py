import numpy as np
import pytest

from openisp.core.frame import Frame, FrameMetadata, PixelRange
from openisp.core.types import CfaPattern, PixelDomain


def synthetic_bayer(pattern: CfaPattern, height: int = 12, width: int = 12) -> np.ndarray:
    values = {"r": 240, "gr": 180, "gb": 176, "b": 120}
    image = np.empty((height, width), dtype=np.uint16)
    for color, index in pattern.slices().items():
        rows, columns = np.indices(image[index].shape)
        image[index] = values[color] + rows * 3 + columns * 2
    image[4, 4] = 700
    return image


@pytest.fixture(params=list(CfaPattern))
def bayer_frame(request):
    pattern = request.param
    return Frame(
        synthetic_bayer(pattern),
        PixelDomain.BAYER,
        PixelRange(0, 1023, bit_depth=10),
        cfa=pattern,
        metadata=FrameMetadata(frame_id=7, analog_gain=1.0),
    )
