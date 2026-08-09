"""Validated, configurable stage execution."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import numpy as np

from openisp.core.config import PipelineConfig
from openisp.core.frame import Frame
from openisp.core.registry import StageRegistry, registry
from openisp.core.stage import PipelineContext, Stage
from openisp.core.types import PixelDomain


@dataclass(frozen=True)
class PipelineResult:
    frame: Frame
    context: PipelineContext
    executed_stages: Tuple[str, ...]
    bypassed_stages: Tuple[str, ...]


class Pipeline:
    def __init__(self, stages: Iterable[Stage], export_directory: Optional[Path] = None) -> None:
        self.stages = tuple(stages)
        self.export_directory = export_directory

    @classmethod
    def from_config(
        cls,
        config: PipelineConfig,
        *,
        stage_registry: StageRegistry = registry,
        export_directory: Optional[Path] = None,
    ) -> "Pipeline":
        stages = [
            stage_registry.create(spec.name, spec.parameters, spec.enabled)
            for spec in config.stages
        ]
        return cls(stages, export_directory=export_directory)

    def validate(self, input_domain: PixelDomain) -> PixelDomain:
        domain = input_domain
        completed: Set[str] = set()
        names: Set[str] = set()
        for stage in self.stages:
            if stage.name in names:
                raise ValueError("duplicate stage name in pipeline: {!r}".format(stage.name))
            names.add(stage.name)
            if not stage.enabled:
                continue
            if stage.requires - completed:
                missing = ", ".join(sorted(stage.requires - completed))
                raise ValueError("stage {!r} has unmet dependencies: {}".format(stage.name, missing))
            if domain not in stage.input_domains:
                accepted = ", ".join(item.value for item in stage.input_domains)
                raise ValueError(
                    "stage {!r} follows domain {!r} but accepts [{}]".format(stage.name, domain.value, accepted)
                )
            domain = stage.output_domain
            completed.add(stage.name)
            completed.update(stage.provides)
        return domain

    def run(self, frame: Frame, context: Optional[PipelineContext] = None) -> PipelineResult:
        self.validate(frame.domain)
        run_context = PipelineContext() if context is None else context
        current = frame
        executed: List[str] = []
        bypassed: List[str] = []
        for index, stage in enumerate(self.stages):
            if not stage.enabled:
                bypassed.append(stage.name)
                continue
            stage.validate_input(current)
            next_frame = stage.process(current, run_context)
            if not isinstance(next_frame, Frame):
                raise TypeError("stage {!r} did not return a Frame".format(stage.name))
            if next_frame.domain != stage.output_domain:
                raise ValueError(
                    "stage {!r} declared {!r} but returned {!r}".format(
                        stage.name, stage.output_domain.value, next_frame.domain.value
                    )
                )
            current = next_frame
            executed.append(stage.name)
            run_context.history.append({"index": index, "stage": stage.name, "domain": current.domain.value})
            if self.export_directory is not None:
                self._export(index, stage.name, current)
        return PipelineResult(current, run_context, tuple(executed), tuple(bypassed))

    def _export(self, index: int, name: str, frame: Frame) -> None:
        assert self.export_directory is not None
        self.export_directory.mkdir(parents=True, exist_ok=True)
        stem = "{:03d}_{}".format(index, name.replace("/", "_"))
        np.save(str(self.export_directory / (stem + ".npy")), frame.data, allow_pickle=False)
        metadata = {
            "domain": frame.domain.value,
            "dtype": str(frame.data.dtype),
            "shape": list(frame.data.shape),
            "range": {
                "minimum": frame.pixel_range.minimum,
                "maximum": frame.pixel_range.maximum,
                "bit_depth": frame.pixel_range.bit_depth,
                "normalized": frame.pixel_range.normalized,
            },
            "frame_id": frame.metadata.frame_id,
            "artifacts": sorted(frame.artifacts),
        }
        (self.export_directory / (stem + ".json")).write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
