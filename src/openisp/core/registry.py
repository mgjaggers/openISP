"""Named stage registry used by configuration-driven pipelines."""

from typing import Any, Callable, Dict, Iterable, Mapping

from openisp.core.stage import Stage

StageFactory = Callable[[Mapping[str, Any], bool], Stage]


class StageRegistry:
    def __init__(self) -> None:
        self._factories: Dict[str, StageFactory] = {}

    def register(self, name: str, factory: StageFactory) -> None:
        if not name or name in self._factories:
            raise ValueError("stage name must be non-empty and unique: {!r}".format(name))
        self._factories[name] = factory

    def create(self, name: str, parameters: Mapping[str, Any], enabled: bool = True) -> Stage:
        try:
            return self._factories[name](parameters, enabled)
        except KeyError as error:
            raise KeyError("unknown stage {!r}; registered: {}".format(name, ", ".join(self.names()))) from error

    def names(self) -> Iterable[str]:
        return tuple(sorted(self._factories))


registry = StageRegistry()


def register_stage(name: str) -> Callable[[type], type]:
    def decorator(stage_type: type) -> type:
        def factory(parameters: Mapping[str, Any], enabled: bool = True) -> Stage:
            return stage_type.from_config(parameters, enabled=enabled)

        registry.register(name, factory)
        return stage_type

    return decorator
