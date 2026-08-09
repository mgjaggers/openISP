"""Versioned JSON configuration for the modular pipeline."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple


@dataclass(frozen=True)
class StageSpec:
    name: str
    enabled: bool = True
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineConfig:
    schema_version: int
    stages: Tuple[StageSpec, ...]
    profile: str = "default"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PipelineConfig":
        version = int(value.get("schema_version", 1))
        if version != 1:
            raise ValueError("unsupported pipeline schema version: {}".format(version))
        stage_values = value.get("stages")
        if not isinstance(stage_values, Iterable) or isinstance(stage_values, (str, bytes, Mapping)):
            raise ValueError("stages must be a list")
        stages = []
        for item in stage_values:
            if not isinstance(item, Mapping) or "name" not in item:
                raise ValueError("each stage must be an object with a name")
            parameters = item.get("parameters", {})
            if not isinstance(parameters, Mapping):
                raise ValueError("stage parameters must be an object")
            stages.append(
                StageSpec(
                    name=str(item["name"]),
                    enabled=bool(item.get("enabled", True)),
                    parameters=dict(parameters),
                )
            )
        return cls(version, tuple(stages), str(value.get("profile", "default")))

    @classmethod
    def load(cls, path: Path) -> "PipelineConfig":
        with path.open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def write_snapshot(self, path: Path) -> None:
        payload = self.to_dict()
        payload["sha256"] = self.digest()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
