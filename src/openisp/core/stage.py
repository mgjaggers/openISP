"""Stage interface and per-run context."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, FrozenSet, Mapping, Tuple

from openisp.core.frame import Frame
from openisp.core.types import PixelDomain


@dataclass
class PipelineContext:
    """Mutable run state kept separate from immutable frame metadata."""

    statistics: Dict[str, Any] = field(default_factory=dict)
    controls: Dict[str, Any] = field(default_factory=dict)
    history: list = field(default_factory=list)


class Stage(ABC):
    """Base contract implemented by every configurable ISP operation."""

    name = "stage"
    input_domains: Tuple[PixelDomain, ...] = tuple(PixelDomain)
    output_domain: PixelDomain = PixelDomain.BAYER
    requires: FrozenSet[str] = frozenset()
    provides: FrozenSet[str] = frozenset()

    def __init__(self, config: Any = None, enabled: bool = True) -> None:
        self.config = config
        self.enabled = enabled

    @classmethod
    def from_config(cls, parameters: Mapping[str, Any], enabled: bool = True) -> "Stage":
        return cls(config=dict(parameters), enabled=enabled)

    def config_dict(self) -> Dict[str, Any]:
        if self.config is None:
            return {}
        if is_dataclass(self.config):
            return asdict(self.config)
        if isinstance(self.config, Mapping):
            return dict(self.config)
        return {"value": repr(self.config)}

    def validate_input(self, frame: Frame) -> None:
        if frame.domain not in self.input_domains:
            accepted = ", ".join(domain.value for domain in self.input_domains)
            raise ValueError(
                "stage {!r} accepts [{}], not {!r}".format(self.name, accepted, frame.domain.value)
            )

    @abstractmethod
    def process(self, frame: Frame, context: PipelineContext) -> Frame:
        """Return a new frame and never rely on undeclared global state."""
