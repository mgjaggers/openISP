"""Typed stage adapters for the original openISP algorithms.

The adapter boundary preserves the public ``model.*`` imports while preventing
the old in-place mutation and implicit-domain conventions from leaking into the
new pipeline.  Algorithm replacements can now happen one stage at a time.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

import numpy as np

from model.aaf import AAF
from model.awb import WBGC
from model.bcc import BCC
from model.blc import BLC
from model.bnf import BNF
from model.ccm import CCM
from model.cfa import CFA
from model.cnf import CNF
from model.csc import CSC
from model.dpc import DPC
from model.eeh import EE
from model.fcs import FCS
from model.gac import GC
from model.hsc import HSC
from model.nlm import NLM
from openisp.core.frame import Frame, PixelRange
from openisp.core.registry import register_stage
from openisp.core.stage import PipelineContext, Stage
from openisp.core.types import PixelDomain


def _tuple(value: Sequence[Any], length: int, name: str) -> Tuple[Any, ...]:
    result = tuple(value)
    if len(result) != length:
        raise ValueError("{} must contain {} values".format(name, length))
    return result


def _matrix(value: Sequence[Sequence[float]], rows: int, columns: int, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (rows, columns):
        raise ValueError("{} must have shape ({}, {})".format(name, rows, columns))
    return result


def _even_bayer(frame: Frame) -> None:
    if frame.data.shape[0] % 2 or frame.data.shape[1] % 2:
        raise ValueError("legacy Bayer stages require even image dimensions")


class _BayerStage(Stage):
    input_domains = (PixelDomain.BAYER,)
    output_domain = PixelDomain.BAYER

    def validate_input(self, frame: Frame) -> None:
        super().validate_input(frame)
        _even_bayer(frame)


@dataclass(frozen=True)
class DpcConfig:
    threshold: int = 30
    mode: str = "gradient"
    clip: int = 1023


@register_stage("dead-pixel-correction")
class DeadPixelCorrectionStage(_BayerStage):
    name = "dead-pixel-correction"

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "DeadPixelCorrectionStage":
        config = DpcConfig(
            threshold=int(parameters.get("threshold", 30)),
            mode=str(parameters.get("mode", "gradient")),
            clip=int(parameters.get("clip", 1023)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = DPC(frame.data.copy(), self.config.threshold, self.config.mode, self.config.clip).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class BlcConfig:
    red: int = 0
    green_red: int = 0
    green_blue: int = 0
    blue: int = 0
    red_fusion: int = 0
    blue_fusion: int = 0
    clip: int = 1023


@register_stage("black-level-compensation")
class BlackLevelStage(_BayerStage):
    name = "black-level-compensation"

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "BlackLevelStage":
        config = BlcConfig(
            red=int(parameters.get("red", 0)),
            green_red=int(parameters.get("green_red", 0)),
            green_blue=int(parameters.get("green_blue", 0)),
            blue=int(parameters.get("blue", 0)),
            red_fusion=int(parameters.get("red_fusion", 0)),
            blue_fusion=int(parameters.get("blue_fusion", 0)),
            clip=int(parameters.get("clip", 1023)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        offsets = [
            self.config.red,
            self.config.green_red,
            self.config.green_blue,
            self.config.blue,
            self.config.red_fusion,
            self.config.blue_fusion,
        ]
        output = BLC(frame.data.copy(), offsets, frame.cfa.value, self.config.clip).execute()
        return frame.evolve(data=output)


@register_stage("anti-aliasing-filter")
class AntiAliasingStage(_BayerStage):
    name = "anti-aliasing-filter"

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "AntiAliasingStage":
        return cls(config={}, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        return frame.evolve(data=AAF(frame.data.copy()).execute())


@dataclass(frozen=True)
class AwbEstimateConfig:
    minimum: float = 1.0e-6
    maximum_gain: float = 8.0


@register_stage("awb-estimate")
class AutoWhiteBalanceEstimatorStage(_BayerStage):
    """Gray-world reference estimator; it publishes gains but never applies them."""

    name = "awb-estimate"
    provides = frozenset({"awb-gains"})

    @classmethod
    def from_config(
        cls, parameters: Mapping[str, Any], enabled: bool = True
    ) -> "AutoWhiteBalanceEstimatorStage":
        config = AwbEstimateConfig(
            minimum=float(parameters.get("minimum", 1.0e-6)),
            maximum_gain=float(parameters.get("maximum_gain", 8.0)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        slices = frame.cfa.slices()
        means = {name: float(np.mean(frame.data[index])) for name, index in slices.items()}
        green = max((means["gr"] + means["gb"]) / 2.0, self.config.minimum)
        gains = {
            "red": min(green / max(means["r"], self.config.minimum), self.config.maximum_gain),
            "green_red": 1.0,
            "green_blue": 1.0,
            "blue": min(green / max(means["b"], self.config.minimum), self.config.maximum_gain),
        }
        context.statistics["awb_gains"] = gains
        return frame.with_artifact("awb-gains", gains)


@dataclass(frozen=True)
class WhiteBalanceConfig:
    red: float = 1.0
    green_red: float = 1.0
    green_blue: float = 1.0
    blue: float = 1.0
    clip: int = 1023
    use_estimated: bool = False


@register_stage("white-balance-gain")
class WhiteBalanceGainStage(_BayerStage):
    name = "white-balance-gain"

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "WhiteBalanceGainStage":
        config = WhiteBalanceConfig(
            red=float(parameters.get("red", 1.0)),
            green_red=float(parameters.get("green_red", 1.0)),
            green_blue=float(parameters.get("green_blue", 1.0)),
            blue=float(parameters.get("blue", 1.0)),
            clip=int(parameters.get("clip", 1023)),
            use_estimated=bool(parameters.get("use_estimated", False)),
        )
        stage = cls(config=config, enabled=enabled)
        if config.use_estimated:
            stage.requires = frozenset({"awb-gains"})
        return stage

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        gains = {
            "red": self.config.red,
            "green_red": self.config.green_red,
            "green_blue": self.config.green_blue,
            "blue": self.config.blue,
        }
        if self.config.use_estimated:
            if "awb-gains" not in frame.artifacts:
                raise ValueError("estimated white-balance gains are missing")
            gains.update(frame.artifacts["awb-gains"])
        parameters = [gains["red"], gains["green_red"], gains["green_blue"], gains["blue"]]
        output = WBGC(frame.data.copy(), parameters, frame.cfa.value, self.config.clip).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class CnfConfig:
    threshold: float = 0.0
    gains: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    clip: int = 1023


@register_stage("chroma-noise-filter")
class ChromaNoiseFilterStage(_BayerStage):
    name = "chroma-noise-filter"

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "ChromaNoiseFilterStage":
        config = CnfConfig(
            threshold=float(parameters.get("threshold", 0.0)),
            gains=_tuple(parameters.get("gains", (1.0, 1.0, 1.0, 1.0)), 4, "gains"),
            clip=int(parameters.get("clip", 1023)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = CNF(
            frame.data.copy(), frame.cfa.value, self.config.threshold, self.config.gains, self.config.clip
        ).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class DemosaicConfig:
    mode: str = "malvar"
    clip: int = 1023


@register_stage("demosaic")
class DemosaicStage(Stage):
    name = "demosaic"
    input_domains = (PixelDomain.BAYER,)
    output_domain = PixelDomain.RGB_LINEAR

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "DemosaicStage":
        return cls(
            config=DemosaicConfig(str(parameters.get("mode", "malvar")), int(parameters.get("clip", 1023))),
            enabled=enabled,
        )

    def validate_input(self, frame: Frame) -> None:
        super().validate_input(frame)
        _even_bayer(frame)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = CFA(frame.data.copy(), self.config.mode, frame.cfa.value, self.config.clip).execute()
        return frame.evolve(data=output, domain=PixelDomain.RGB_LINEAR, cfa=None)


@dataclass(frozen=True)
class MatrixConfig:
    matrix: Tuple[Tuple[float, float, float, float], ...]


@register_stage("color-correction-matrix")
class ColorCorrectionStage(Stage):
    name = "color-correction-matrix"
    input_domains = (PixelDomain.RGB_LINEAR,)
    output_domain = PixelDomain.RGB_LINEAR

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "ColorCorrectionStage":
        default = ((1024, 0, 0, 0), (0, 1024, 0, 0), (0, 0, 1024, 0))
        matrix = _matrix(parameters.get("matrix", default), 3, 4, "matrix")
        return cls(config=MatrixConfig(tuple(tuple(row) for row in matrix)), enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = CCM(frame.data.copy(), np.asarray(self.config.matrix)).execute()
        return frame.evolve(data=output, pixel_range=PixelRange(0, 255, bit_depth=8))


@dataclass(frozen=True)
class GammaConfig:
    gamma: float = 0.5
    bit_depth: int = 10
    mode: str = "rgb"


@register_stage("gamma")
class GammaStage(Stage):
    name = "gamma"
    input_domains = (PixelDomain.RGB_LINEAR,)
    output_domain = PixelDomain.RGB_ENCODED

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "GammaStage":
        config = GammaConfig(
            gamma=float(parameters.get("gamma", 0.5)),
            bit_depth=int(parameters.get("bit_depth", 10)),
            mode=str(parameters.get("mode", "rgb")),
        )
        if config.gamma <= 0 or config.bit_depth <= 0:
            raise ValueError("gamma and bit depth must be positive")
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        maximum = 2 ** self.config.bit_depth
        lut = {
            index: round(pow(float(index) / maximum, self.config.gamma) * maximum)
            for index in range(maximum)
        }
        if np.min(frame.data) < 0 or np.max(frame.data) >= maximum:
            raise ValueError("gamma input falls outside its configured lookup table")
        output = GC(frame.data.copy(), lut, self.config.mode).execute()
        return frame.evolve(data=output, domain=PixelDomain.RGB_ENCODED)


@register_stage("color-space-conversion")
class ColorSpaceConversionStage(Stage):
    name = "color-space-conversion"
    input_domains = (PixelDomain.RGB_ENCODED,)
    output_domain = PixelDomain.YUV

    @classmethod
    def from_config(
        cls, parameters: Mapping[str, Any], enabled: bool = True
    ) -> "ColorSpaceConversionStage":
        default = (
            (0.257 * 1024, 0.504 * 1024, 0.098 * 1024, 16 * 1024),
            (-0.148 * 1024, -0.291 * 1024, 0.439 * 1024, 128 * 1024),
            (0.439 * 1024, -0.368 * 1024, -0.071 * 1024, 128 * 1024),
        )
        matrix = _matrix(parameters.get("matrix", default), 3, 4, "matrix")
        return cls(config=MatrixConfig(tuple(tuple(row) for row in matrix)), enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = CSC(frame.data.copy(), np.asarray(self.config.matrix)).execute()
        return frame.evolve(
            data=output,
            domain=PixelDomain.YUV,
            pixel_range=PixelRange(0, 255, bit_depth=8),
        )


@dataclass(frozen=True)
class NlmConfig:
    patch_radius: int = 1
    search_radius: int = 4
    strength: float = 15.0
    clip: int = 255


@register_stage("non-local-means")
class NonLocalMeansStage(Stage):
    name = "non-local-means"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "NonLocalMeansStage":
        config = NlmConfig(
            patch_radius=int(parameters.get("patch_radius", 1)),
            search_radius=int(parameters.get("search_radius", 4)),
            strength=float(parameters.get("strength", 15.0)),
            clip=int(parameters.get("clip", 255)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = frame.data.copy()
        output[:, :, 0] = NLM(
            frame.data[:, :, 0].copy(),
            self.config.patch_radius,
            self.config.search_radius,
            self.config.strength,
            self.config.clip,
        ).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class BilateralConfig:
    distance_weights: Tuple[Tuple[float, ...], ...]
    range_weights: Tuple[float, float, float, float]
    range_thresholds: Tuple[float, float, float]
    clip: int = 255


_DEFAULT_DISTANCE = (
    (8, 12, 32, 12, 8),
    (12, 64, 128, 64, 12),
    (32, 128, 1024, 128, 32),
    (12, 64, 128, 64, 12),
    (8, 12, 32, 12, 8),
)


@register_stage("bilateral-denoise")
class BilateralDenoiseStage(Stage):
    name = "bilateral-denoise"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "BilateralDenoiseStage":
        distance = _matrix(parameters.get("distance_weights", _DEFAULT_DISTANCE), 5, 5, "distance_weights")
        config = BilateralConfig(
            distance_weights=tuple(tuple(row) for row in distance),
            range_weights=_tuple(parameters.get("range_weights", (0, 8, 16, 32)), 4, "range_weights"),
            range_thresholds=_tuple(
                parameters.get("range_thresholds", (128, 32, 8)), 3, "range_thresholds"
            ),
            clip=int(parameters.get("clip", 255)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = frame.data.copy()
        output[:, :, 0] = BNF(
            frame.data[:, :, 0].copy(),
            np.asarray(self.config.distance_weights),
            self.config.range_weights,
            self.config.range_thresholds,
            self.config.clip,
        ).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class EdgeConfig:
    kernel: Tuple[Tuple[float, ...], ...]
    gains: Tuple[float, float]
    thresholds: Tuple[float, float]
    edge_clip: Tuple[float, float]


_DEFAULT_EDGE = ((-1, 0, -1, 0, -1), (-1, 0, 8, 0, -1), (-1, 0, -1, 0, -1))


@register_stage("edge-enhancement")
class EdgeEnhancementStage(Stage):
    name = "edge-enhancement"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV
    provides = frozenset({"edge-map"})

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "EdgeEnhancementStage":
        kernel = _matrix(parameters.get("kernel", _DEFAULT_EDGE), 3, 5, "kernel")
        config = EdgeConfig(
            kernel=tuple(tuple(row) for row in kernel),
            gains=_tuple(parameters.get("gains", (32, 128)), 2, "gains"),
            thresholds=_tuple(parameters.get("thresholds", (32, 64)), 2, "thresholds"),
            edge_clip=_tuple(parameters.get("edge_clip", (-64, 64)), 2, "edge_clip"),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        luma, edge_map = EE(
            frame.data[:, :, 0].copy(),
            np.asarray(self.config.kernel),
            self.config.gains,
            self.config.thresholds,
            self.config.edge_clip,
        ).execute()
        output = frame.data.copy()
        output[:, :, 0] = luma
        context.statistics["edge_map"] = edge_map
        return frame.evolve(data=output).with_artifact("edge-map", edge_map)


@dataclass(frozen=True)
class FcsConfig:
    edge: Tuple[float, float] = (32, 64)
    gain: float = 32
    intercept: float = 2
    slope: float = 3


@register_stage("false-color-suppression")
class FalseColorSuppressionStage(Stage):
    name = "false-color-suppression"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV
    requires = frozenset({"edge-map"})

    @classmethod
    def from_config(
        cls, parameters: Mapping[str, Any], enabled: bool = True
    ) -> "FalseColorSuppressionStage":
        config = FcsConfig(
            edge=_tuple(parameters.get("edge", (32, 64)), 2, "edge"),
            gain=float(parameters.get("gain", 32)),
            intercept=float(parameters.get("intercept", 2)),
            slope=float(parameters.get("slope", 3)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        edge_map = frame.artifacts.get("edge-map")
        if edge_map is None:
            raise ValueError("false-color suppression requires an edge map")
        chroma = FCS(
            frame.data[:, :, 1:3].copy(),
            edge_map,
            self.config.edge,
            self.config.gain,
            self.config.intercept,
            self.config.slope,
        ).execute()
        output = frame.data.copy()
        output[:, :, 1:3] = chroma
        return frame.evolve(data=output)


@dataclass(frozen=True)
class HueSaturationConfig:
    hue_degrees: int = 0
    saturation: int = 256
    clip: int = 255


@register_stage("hue-saturation")
class HueSaturationStage(Stage):
    name = "hue-saturation"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "HueSaturationStage":
        config = HueSaturationConfig(
            hue_degrees=int(parameters.get("hue_degrees", 0)) % 360,
            saturation=int(parameters.get("saturation", 256)),
            clip=int(parameters.get("clip", 255)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = frame.data.copy()
        output[:, :, 1:3] = HSC(
            frame.data[:, :, 1:3].copy(),
            self.config.hue_degrees,
            self.config.saturation,
            self.config.clip,
        ).execute()
        return frame.evolve(data=output)


@dataclass(frozen=True)
class BrightnessContrastConfig:
    brightness: float = 0.0
    contrast: float = 1.0
    clip: int = 255


@register_stage("brightness-contrast")
class BrightnessContrastStage(Stage):
    name = "brightness-contrast"
    input_domains = (PixelDomain.YUV,)
    output_domain = PixelDomain.YUV

    @classmethod
    def from_config(
        cls, parameters: Mapping[str, Any], enabled: bool = True
    ) -> "BrightnessContrastStage":
        config = BrightnessContrastConfig(
            brightness=float(parameters.get("brightness", 0)),
            contrast=float(parameters.get("contrast", 1.0)),
            clip=int(parameters.get("clip", 255)),
        )
        return cls(config=config, enabled=enabled)

    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        output = frame.data.copy()
        output[:, :, 0] = BCC(
            frame.data[:, :, 0].copy(),
            self.config.brightness,
            self.config.contrast,
            self.config.clip,
        ).execute()
        return frame.evolve(data=output)
