"""World container for the v0.3 prototype."""

from __future__ import annotations

from dataclasses import dataclass, field

from worldline.models import BaselineTile, Entity, LocalBaselinePatch, Perturbation
from worldline.provenance import ProvenanceGraph

Coord = tuple[int, int]


@dataclass
class World:
    seed: int
    size: int
    baseline: dict[Coord, BaselineTile] = field(default_factory=dict)
    entities: dict[int, Entity] = field(default_factory=dict)
    perturbations: dict[int, Perturbation] = field(default_factory=dict)
    patches: dict[int, LocalBaselinePatch] = field(default_factory=dict)
    provenance: ProvenanceGraph = field(default_factory=ProvenanceGraph)

    def entity_by_name(self, name: str) -> Entity | None:
        for entity in self.entities.values():
            if entity.name == name:
                return entity
        return None

    def entities_by_type(self, entity_type: str) -> list[Entity]:
        return [entity for entity in self.entities.values() if entity.type == entity_type]
