"""Reference NumPy stages adapted from the original openISP implementation."""

# Importing legacy registers every built-in stage with the global registry.
from openisp.stages.legacy import (  # noqa: F401
    AntiAliasingStage,
    AutoWhiteBalanceEstimatorStage,
    BilateralDenoiseStage,
    BlackLevelStage,
    BrightnessContrastStage,
    ChromaNoiseFilterStage,
    ColorCorrectionStage,
    ColorSpaceConversionStage,
    DeadPixelCorrectionStage,
    DemosaicStage,
    EdgeEnhancementStage,
    FalseColorSuppressionStage,
    GammaStage,
    HueSaturationStage,
    NonLocalMeansStage,
    WhiteBalanceGainStage,
)
