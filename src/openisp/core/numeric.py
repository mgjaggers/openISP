"""Explicit rounding, saturation and output-quantization helpers."""

from dataclasses import dataclass
from enum import Enum
from typing import Union

import numpy as np

Number = Union[int, float]


class RoundingMode(str, Enum):
    NEAREST_EVEN = "nearest-even"
    HALF_UP = "half-up"
    TRUNCATE = "truncate"


@dataclass(frozen=True)
class NumericPolicy:
    """Numerical rules applied at an explicit stage boundary."""

    minimum: Number
    maximum: Number
    dtype: str
    rounding: RoundingMode = RoundingMode.NEAREST_EVEN
    saturate: bool = True

    def apply(self, values: np.ndarray) -> np.ndarray:
        work = np.asarray(values, dtype=np.float64)
        if self.rounding == RoundingMode.NEAREST_EVEN:
            work = np.rint(work)
        elif self.rounding == RoundingMode.HALF_UP:
            work = np.floor(work + 0.5)
        elif self.rounding == RoundingMode.TRUNCATE:
            work = np.trunc(work)
        if self.saturate:
            work = np.clip(work, self.minimum, self.maximum)
        return work.astype(np.dtype(self.dtype), copy=False)


def safe_working_copy(values: np.ndarray) -> np.ndarray:
    """Promote integers before arithmetic so unsigned wraparound is impossible."""

    if np.issubdtype(values.dtype, np.integer):
        return values.astype(np.int64)
    return values.astype(np.float64)
