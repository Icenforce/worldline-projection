"""Core data models for Worldline Projection v0.3.

These models are intentionally small. They define the spine of the causal-provenance
prototype without committing to a full game engine or visual layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

Coord = tuple[int, int]


class EntityType(StrEnum):
    SETTLEMENT = "Settlement"
    ROAD = "Road"
    MINE = "Mine"
    LUMBER_CAMP = "LumberCamp"
    FORT = "Fort"
    RUIN = "Ruin"
    BATTLEFIELD = "Battlefield"


class SettlementSubtype(StrEnum):
    AGRARIAN_VILLAGE = "AgrarianVillage"
    MINING_CAMP = "MiningCamp"
    TRADE_TOWN = "TradeTown"
    FORTIFIED_TOWN = "FortifiedTown"
    ISOLATED_SHRINE_SETTLEMENT = "IsolatedShrineSettlement"


class NodeType(StrEnum):
    SUBSTRATE_PRECONDITION = "SubstratePrecondition"
    GENERATED_ENTITY = "GeneratedEntity"
    HISTORICAL_EVENT = "HistoricalEvent"
    PERTURBATION_EVENT = "PerturbationEvent"
    COMPACTION_ARCHIVE_EVENT = "CompactionArchiveEvent"
    ANOMALY = "Anomaly"


class EdgeType(StrEnum):
    REQUIRES = "REQUIRES"
    ENABLES = "ENABLES"
    SUPPLIES = "SUPPLIES"
    TRANSITS = "TRANSITS"
    LOCATES = "LOCATES"
    CAUSES = "CAUSES"
    DAMAGES = "DAMAGES"
    INVALIDATES = "INVALIDATES"
    REPLACES = "REPLACES"
    REPAIRS = "REPAIRS"
    DESCENDS_FROM = "DESCENDS_FROM"


class PerturbationType(StrEnum):
    RESOURCE_DESTRUCTION = "ResourceDestruction"
    RESOURCE_EXTRACTION = "ResourceExtraction"
    CONSTRUCTION = "Construction"
    ENTITY_DAMAGE = "EntityDamage"
    ENTITY_REMOVAL = "EntityRemoval"
    ROUTE_CUT = "RouteCut"


@dataclass(frozen=True)
class BaselineTile:
    """Immutable seed-derived natural substrate tile."""

    x: int
    y: int
    elevation: float
    slope: float
    water_flow: float
    basin_id: int
    biome: str
    fertility: float
    timber: float
    iron: float
    coal: float


@dataclass
class EntityState:
    integrity: float = 1.0
    wealth: float = 0.5
    function: float = 1.0
    active: bool = True
    stale: bool = False
    status_label: str = "Stable"

    def clamp(self) -> None:
        self.integrity = min(1.0, max(0.0, self.integrity))
        self.wealth = min(1.0, max(0.0, self.wealth))
        self.function = min(1.0, max(0.0, self.function))
        self.active = self.integrity > 0.0 and self.function > 0.0
        if self.wealth < 0.25:
            self.status_label = "Destitute"
        elif self.wealth < 0.45:
            self.status_label = "Poor"
        elif self.wealth > 0.75:
            self.status_label = "Affluent"
        else:
            self.status_label = "Stable"


@dataclass
class Entity:
    id: int
    type: EntityType
    subtype: str | None
    name: str
    coordinates: list[Coord]
    state: EntityState
    root_provenance_id: int


@dataclass
class ProvenanceNode:
    id: int
    node_type: NodeType
    label: str
    entity_id: int | None = None
    event_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvenanceEdge:
    id: int
    source_node_id: int
    target_node_id: int
    edge_type: EdgeType
    weight: float = 1.0
    payload: dict[str, Any] = field(default_factory=dict)
    load_bearing: bool = True


@dataclass
class Perturbation:
    id: int
    t: int
    type: PerturbationType
    origin: Coord
    radius: int
    magnitude: float
    target_layer: str
    target_entity_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatchTileDelta:
    timber_delta: float = 0.0
    iron_delta: float = 0.0
    coal_delta: float = 0.0
    fertility_delta: float = 0.0


@dataclass
class LocalBaselinePatch:
    id: int
    region_id: str
    created_at_t: int
    tile_overrides: dict[Coord, PatchTileDelta] = field(default_factory=dict)
    archive_event_ids: list[int] = field(default_factory=list)
