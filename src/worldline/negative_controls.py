"""Minimal negative-control harness for Gate 5 comparisons.

Control C is intentionally coherent at generation time but relies on post-hoc
explanation templates rather than executable provenance. It should therefore
produce plausible initial descriptions while failing to preserve causal validity
through perturbation and compaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worldline.generate import generate_world
from worldline.models import BaselineTile, EntityState, EntityType
from worldline.perturb import compact_timber_collapse, find_timber_dependency_pair, inject_timber_destruction
from worldline.placement import best_resource_candidate_near, choose_spread_candidates, find_settlement_candidates
from worldline.query import explain_entity
from worldline.substrate import generate_substrate

Coord = tuple[int, int]


@dataclass
class ControlEntity:
    id: int
    type: EntityType
    subtype: str | None
    name: str
    coordinates: list[Coord]
    state: EntityState
    explanation_template: str
    supporting_resource: str | None = None
    supporting_coord: Coord | None = None
    supporting_entity_id: int | None = None
    notes: dict[str, object] = field(default_factory=dict)


@dataclass
class ControlWorld:
    seed: int
    size: int
    baseline: dict[Coord, BaselineTile]
    entities: dict[int, ControlEntity] = field(default_factory=dict)
    perturbations: list[dict[str, object]] = field(default_factory=list)
    compaction_archives: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class NegativeControlComparison:
    worldline_post_perturbation_valid: bool
    control_post_perturbation_valid: bool
    worldline_compaction_retention_valid: bool
    control_compaction_retention_valid: bool
    worldline_contradiction_count: int
    control_contradiction_count: int
    worldline_explanation_depth: int
    control_explanation_depth: int


def generate_control_c(seed: int = 12345, size: int = 128, *, settlement_count: int = 5) -> ControlWorld:
    baseline = generate_substrate(seed=seed, size=size)
    world = ControlWorld(seed=seed, size=size, baseline=baseline)

    settlement_candidates = find_settlement_candidates(_PlacementWorldView(baseline=baseline, size=size))
    chosen = choose_spread_candidates(
        settlement_candidates,
        count=settlement_count,
        min_distance=max(8, size // 10),
    )
    if not chosen:
        raise RuntimeError("control generator found no coherent settlement candidates")

    next_entity_id = 1
    for index, candidate in enumerate(chosen, start=1):
        tile = baseline[candidate.coord]
        lumber_candidate = best_resource_candidate_near(
            _PlacementWorldView(baseline=baseline, size=size),
            candidate.coord,
            resource="timber",
            max_distance=max(12, size // 8),
        )
        settlement = ControlEntity(
            id=next_entity_id,
            type=EntityType.SETTLEMENT,
            subtype=candidate.subtype,
            name=f"ControlSettlement_{index:02d}",
            coordinates=[candidate.coord],
            state=EntityState(
                integrity=1.0,
                wealth=min(0.9, 0.35 + candidate.score * 0.45),
                function=1.0,
                active=True,
            ),
            explanation_template=(
                f"{candidate.subtype} chosen at {candidate.coord} because fertility={tile.fertility:.2f}, "
                f"water_flow={tile.water_flow:.2f}, slope={tile.slope:.2f}, and nearby timber promises "
                f"construction support."
            ),
            supporting_resource="timber" if lumber_candidate is not None else None,
            supporting_coord=lumber_candidate.coord if lumber_candidate is not None else None,
        )
        settlement.state.clamp()
        world.entities[settlement.id] = settlement
        next_entity_id += 1

        if lumber_candidate is not None and lumber_candidate.value > 0.25:
            lumber = ControlEntity(
                id=next_entity_id,
                type=EntityType.LUMBER_CAMP,
                subtype=None,
                name=f"ControlLumberCamp_{next_entity_id:02d}",
                coordinates=[lumber_candidate.coord],
                state=EntityState(integrity=1.0, wealth=0.5, function=max(0.1, lumber_candidate.value), active=True),
                explanation_template=(
                    f"Lumber camp placed at {lumber_candidate.coord} because local timber={lumber_candidate.value:.2f} "
                    f"and the nearest settlement expects construction material."
                ),
                supporting_resource="timber",
                supporting_coord=lumber_candidate.coord,
                supporting_entity_id=settlement.id,
            )
            lumber.state.clamp()
            world.entities[lumber.id] = lumber
            settlement.supporting_entity_id = lumber.id
            next_entity_id += 1

    return world


@dataclass(frozen=True)
class ControlDependencyPair:
    settlement_id: int
    lumber_camp_id: int


def find_control_timber_dependency_pair(world: ControlWorld) -> ControlDependencyPair:
    best: tuple[float, int, int] | None = None
    for settlement in world.entities.values():
        if settlement.type != EntityType.SETTLEMENT or settlement.supporting_entity_id is None:
            continue
        lumber = world.entities.get(settlement.supporting_entity_id)
        if lumber is None or lumber.type != EntityType.LUMBER_CAMP:
            continue
        score = float(lumber.state.function)
        candidate = (score, settlement.id, lumber.id)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        raise RuntimeError("control world has no timber dependency pair")
    return ControlDependencyPair(settlement_id=best[1], lumber_camp_id=best[2])


def inject_control_timber_destruction(world: ControlWorld, *, magnitude: float = 0.9, t: int = 100) -> dict[str, object]:
    pair = find_control_timber_dependency_pair(world)
    settlement = world.entities[pair.settlement_id]
    lumber = world.entities[pair.lumber_camp_id]

    perturbation = {
        "id": len(world.perturbations) + 1,
        "t": t,
        "type": "ResourceDestruction",
        "target_layer": "timber",
        "origin": lumber.coordinates[0],
        "magnitude": magnitude,
        "settlement_id": settlement.id,
        "lumber_camp_id": lumber.id,
    }
    world.perturbations.append(perturbation)

    lumber.state.function = max(0.0, lumber.state.function * (1.0 - magnitude * 0.83))
    lumber.state.integrity = max(0.0, lumber.state.integrity - magnitude * 0.25)
    lumber.state.stale = True
    lumber.state.clamp()

    settlement.state.wealth = max(0.0, settlement.state.wealth - magnitude * 0.40)
    settlement.state.function = max(0.0, settlement.state.function - magnitude * 0.20)
    settlement.state.stale = True
    settlement.state.clamp()
    return perturbation


def compact_control_timber_collapse(world: ControlWorld, *, t: int = 142) -> dict[str, object]:
    pair = find_control_timber_dependency_pair(world)
    archive = {
        "id": len(world.compaction_archives) + 1,
        "t": t,
        "summary": "timber collapse compacted into local archive summary",
        "affected_entities": [pair.settlement_id, pair.lumber_camp_id],
    }
    world.compaction_archives.append(archive)
    return archive


def explain_control_entity(world: ControlWorld, entity_id: int) -> str:
    entity = world.entities[entity_id]
    lines = [
        f"{entity.name} [{entity.type}]",
        f"status={entity.state.status_label} wealth={entity.state.wealth:.2f} function={entity.state.function:.2f}",
        "posthoc_explanation:",
        f"- {entity.explanation_template}",
    ]
    if world.compaction_archives:
        lines.append("- local state compacted into summary records")
    return "\n".join(lines)


def compare_worldline_vs_control_c(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    worldline = generate_world(seed=seed, size=size)
    worldline_settlement_id, _ = find_timber_dependency_pair(worldline)
    inject_timber_destruction(worldline, magnitude=0.9, t=100)
    compact_timber_collapse(worldline, t=142)
    worldline_explanation = explain_entity(worldline, worldline_settlement_id)

    control = generate_control_c(seed=seed, size=size)
    control_pair = find_control_timber_dependency_pair(control)
    inject_control_timber_destruction(control, magnitude=0.9, t=100)
    compact_control_timber_collapse(control, t=142)
    control_explanation = explain_control_entity(control, control_pair.settlement_id)

    return NegativeControlComparison(
        worldline_post_perturbation_valid=_worldline_post_perturbation_valid(worldline_explanation),
        control_post_perturbation_valid=_control_post_perturbation_valid(control_explanation),
        worldline_compaction_retention_valid=_worldline_compaction_retention_valid(worldline_explanation),
        control_compaction_retention_valid=_control_compaction_retention_valid(control_explanation),
        worldline_contradiction_count=_count_worldline_contradictions(worldline_explanation),
        control_contradiction_count=_count_control_contradictions(control, control_pair.settlement_id, control_explanation),
        worldline_explanation_depth=_explanation_depth(worldline_explanation),
        control_explanation_depth=_explanation_depth(control_explanation),
    )


def _worldline_post_perturbation_valid(explanation: str) -> bool:
    return "timber destruction" in explanation and "DAMAGES" in explanation


def _worldline_compaction_retention_valid(explanation: str) -> bool:
    return "CompactionArchiveEvent" in explanation and "timber collapse archive" in explanation


def _control_post_perturbation_valid(explanation: str) -> bool:
    return "timber destruction" in explanation or "ResourceDestruction" in explanation


def _control_compaction_retention_valid(explanation: str) -> bool:
    return "timber collapse archive" in explanation or "CompactionArchiveEvent" in explanation


def _count_worldline_contradictions(explanation: str) -> int:
    contradictions = 0
    if "status=Poor" in explanation and "timber destruction" not in explanation:
        contradictions += 1
    if "status=Poor" in explanation and "CompactionArchiveEvent" not in explanation:
        contradictions += 1
    return contradictions


def _count_control_contradictions(world: ControlWorld, entity_id: int, explanation: str) -> int:
    entity = world.entities[entity_id]
    contradictions = 0
    if entity.state.status_label == "Poor" and "promises construction support" in explanation:
        contradictions += 1
    if world.compaction_archives and "timber collapse" not in explanation:
        contradictions += 1
    if world.perturbations and "timber destruction" not in explanation:
        contradictions += 1
    return contradictions


def _explanation_depth(explanation: str) -> int:
    return sum(1 for line in explanation.splitlines() if line.strip().startswith("-"))


@dataclass(frozen=True)
class _PlacementWorldView:
    baseline: dict[Coord, BaselineTile]
    size: int
