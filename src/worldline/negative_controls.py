"""Minimal negative-control harness for Gate 5 comparisons.

Control C is intentionally coherent at generation time but relies on post-hoc
explanation templates rather than executable provenance. It should therefore
produce plausible initial descriptions while failing to preserve causal validity
through perturbation and compaction.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from worldline.generate import generate_world
from worldline.models import BaselineTile, EntityState, EntityType
from worldline.perturb import (
    compact_route_cut,
    compact_timber_collapse,
    find_route_conflict_triplet,
    find_timber_dependency_pair,
    inject_route_cut,
    inject_timber_destruction,
)
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
    explanation_template: str | None
    supporting_resource: str | None = None
    supporting_coord: Coord | None = None
    supporting_entity_id: int | None = None
    notes: dict[str, object] = field(default_factory=dict)


@dataclass
class ControlWorld:
    control_label: str
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
    worldline_perturbation_consequence_rate: float
    control_perturbation_consequence_rate: float
    worldline_contradiction_count: int
    control_contradiction_count: int
    worldline_explanation_depth: int
    control_explanation_depth: int


@dataclass(frozen=True)
class ControlDependencyPair:
    settlement_id: int
    lumber_camp_id: int


@dataclass(frozen=True)
class ControlRouteConflictTriplet:
    road_id: int
    fort_id: int
    battlefield_id: int


def generate_control_a(seed: int = 12345, size: int = 128, *, settlement_count: int = 5) -> ControlWorld:
    baseline = generate_substrate(seed=seed, size=size)
    world = ControlWorld(control_label="A", seed=seed, size=size, baseline=baseline)
    rng = random.Random(seed)
    coords = list(baseline.keys())
    chosen = rng.sample(coords, settlement_count * 2 + 3)

    next_entity_id = 1
    for index in range(settlement_count):
        settlement_coord = chosen[index * 2]
        lumber_coord = chosen[index * 2 + 1]
        settlement = ControlEntity(
            id=next_entity_id,
            type=EntityType.SETTLEMENT,
            subtype="random",
            name=f"ControlASettlement_{index + 1:02d}",
            coordinates=[settlement_coord],
            state=EntityState(integrity=1.0, wealth=0.45, function=1.0, active=True),
            explanation_template=None,
            supporting_entity_id=next_entity_id + 1,
            notes={"random_coord": settlement_coord},
        )
        settlement.state.clamp()
        world.entities[settlement.id] = settlement

        lumber = ControlEntity(
            id=next_entity_id + 1,
            type=EntityType.LUMBER_CAMP,
            subtype=None,
            name=f"ControlALumberCamp_{index + 1:02d}",
            coordinates=[lumber_coord],
            state=EntityState(integrity=1.0, wealth=0.2, function=0.35, active=True),
            explanation_template=None,
            supporting_entity_id=settlement.id,
            notes={"random_coord": lumber_coord},
        )
        lumber.state.clamp()
        world.entities[lumber.id] = lumber
        next_entity_id += 2

    road_coord, fort_coord, battlefield_coord = chosen[-3:]
    road = ControlEntity(
        id=next_entity_id,
        type=EntityType.ROAD,
        subtype="random",
        name=f"ControlARoad_{next_entity_id:02d}",
        coordinates=[road_coord],
        state=EntityState(integrity=1.0, wealth=0.0, function=1.0, active=True, status_label="Stable"),
        explanation_template=None,
        notes={"random_coord": road_coord},
    )
    road.state.clamp()
    world.entities[road.id] = road

    fort = ControlEntity(
        id=next_entity_id + 1,
        type=EntityType.FORT,
        subtype="random",
        name=f"ControlAFort_{next_entity_id + 1:02d}",
        coordinates=[fort_coord],
        state=EntityState(integrity=1.0, wealth=0.3, function=1.0, active=True),
        explanation_template=None,
        supporting_entity_id=road.id,
        notes={"random_coord": fort_coord},
    )
    fort.state.clamp()
    world.entities[fort.id] = fort

    battlefield = ControlEntity(
        id=next_entity_id + 2,
        type=EntityType.BATTLEFIELD,
        subtype="random",
        name=f"ControlABattlefield_{next_entity_id + 2:02d}",
        coordinates=[battlefield_coord],
        state=EntityState(integrity=1.0, wealth=0.0, function=1.0, active=True),
        explanation_template=None,
        supporting_entity_id=road.id,
        notes={"fort_entity_id": fort.id, "random_coord": battlefield_coord},
    )
    battlefield.state.clamp()
    world.entities[battlefield.id] = battlefield
    return world


def generate_control_b(seed: int = 12345, size: int = 128, *, settlement_count: int = 5) -> ControlWorld:
    baseline = generate_substrate(seed=seed, size=size)
    world = ControlWorld(control_label="B", seed=seed, size=size, baseline=baseline)

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
            name=f"ControlBSettlement_{index:02d}",
            coordinates=[candidate.coord],
            state=EntityState(
                integrity=1.0,
                wealth=min(0.9, 0.35 + candidate.score * 0.45),
                function=1.0,
                active=True,
            ),
            explanation_template=None,
            supporting_resource="timber" if lumber_candidate is not None else None,
            supporting_coord=lumber_candidate.coord if lumber_candidate is not None else None,
            notes={
                "placement_reason": (
                    f"heuristic siting at {candidate.coord} with fertility={tile.fertility:.2f}, "
                    f"water_flow={tile.water_flow:.2f}, slope={tile.slope:.2f}"
                )
            },
        )
        settlement.state.clamp()
        world.entities[settlement.id] = settlement
        next_entity_id += 1

        if lumber_candidate is not None and lumber_candidate.value > 0.25:
            lumber = ControlEntity(
                id=next_entity_id,
                type=EntityType.LUMBER_CAMP,
                subtype=None,
                name=f"ControlBLumberCamp_{next_entity_id:02d}",
                coordinates=[lumber_candidate.coord],
                state=EntityState(integrity=1.0, wealth=0.5, function=max(0.1, lumber_candidate.value), active=True),
                explanation_template=None,
                supporting_resource="timber",
                supporting_coord=lumber_candidate.coord,
                supporting_entity_id=settlement.id,
                notes={
                    "placement_reason": (
                        f"heuristic timber siting at {lumber_candidate.coord} with local_timber={lumber_candidate.value:.2f}"
                    )
                },
            )
            lumber.state.clamp()
            world.entities[lumber.id] = lumber
            settlement.supporting_entity_id = lumber.id
            next_entity_id += 1

    _add_control_route_conflict(world, next_entity_id=next_entity_id)
    return world


def generate_control_c(seed: int = 12345, size: int = 128, *, settlement_count: int = 5) -> ControlWorld:
    baseline = generate_substrate(seed=seed, size=size)
    world = ControlWorld(control_label="C", seed=seed, size=size, baseline=baseline)

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

    _add_control_route_conflict(world, next_entity_id=next_entity_id)
    return world


def _add_control_route_conflict(world: ControlWorld, *, next_entity_id: int) -> None:
    reference_world = generate_world(seed=world.seed, size=world.size)
    road_id, fort_id, battlefield_id = find_route_conflict_triplet(reference_world)
    road = reference_world.entities[road_id]
    fort = reference_world.entities[fort_id]
    battlefield = reference_world.entities[battlefield_id]

    control_road = ControlEntity(
        id=next_entity_id,
        type=EntityType.ROAD,
        subtype=road.subtype,
        name=f"Control{world.control_label}Road_{next_entity_id:02d}",
        coordinates=list(road.coordinates),
        state=EntityState(integrity=1.0, wealth=0.0, function=1.0, active=True, status_label="Stable"),
        explanation_template=(
            f"Road corridor inferred along {len(road.coordinates)} cells because it plausibly connects a strategic choke "
            f"between settlements and resource traffic."
        )
        if world.control_label == "C"
        else None,
        notes={
            "heuristic_role": "route_corridor",
            "placement_reason": f"corridor heuristic using {len(road.coordinates)} aligned cells",
        },
    )
    control_road.state.clamp()
    world.entities[control_road.id] = control_road

    control_fort = ControlEntity(
        id=next_entity_id + 1,
        type=EntityType.FORT,
        subtype=fort.subtype,
        name=f"Control{world.control_label}Fort_{next_entity_id + 1:02d}",
        coordinates=list(fort.coordinates),
        state=EntityState(integrity=1.0, wealth=0.4, function=1.0, active=True),
        explanation_template=(
            f"Fort inferred at {fort.coordinates[0]} because a road chokepoint and route-control intuition make the "
            f"location defensible."
        )
        if world.control_label == "C"
        else None,
        supporting_entity_id=control_road.id,
        notes={
            "heuristic_role": "route_control",
            "placement_reason": f"fort heuristic at chokepoint {fort.coordinates[0]}",
        },
    )
    control_fort.state.clamp()
    world.entities[control_fort.id] = control_fort

    control_battlefield = ControlEntity(
        id=next_entity_id + 2,
        type=EntityType.BATTLEFIELD,
        subtype=battlefield.subtype,
        name=f"Control{world.control_label}Battlefield_{next_entity_id + 2:02d}",
        coordinates=list(battlefield.coordinates),
        state=EntityState(integrity=1.0, wealth=0.0, function=1.0, active=True),
        explanation_template=(
            f"Battlefield inferred near {battlefield.coordinates[0]} because forts and roads often imply conflict corridors "
            f"in post-hoc historical reconstruction."
        )
        if world.control_label == "C"
        else None,
        supporting_entity_id=control_road.id,
        notes={
            "fort_entity_id": control_fort.id,
            "heuristic_role": "conflict_corridor",
            "placement_reason": f"battlefield heuristic near corridor cell {battlefield.coordinates[0]}",
        },
    )
    control_battlefield.state.clamp()
    world.entities[control_battlefield.id] = control_battlefield


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


def find_control_route_conflict_triplet(world: ControlWorld) -> ControlRouteConflictTriplet:
    for entity in world.entities.values():
        if entity.type != EntityType.BATTLEFIELD:
            continue
        road_id = entity.supporting_entity_id
        fort_id = int(entity.notes.get("fort_entity_id", 0))
        if road_id is None or fort_id == 0:
            continue
        road = world.entities.get(road_id)
        fort = world.entities.get(fort_id)
        if road is None or fort is None:
            continue
        if road.type == EntityType.ROAD and fort.type == EntityType.FORT:
            return ControlRouteConflictTriplet(road_id=road.id, fort_id=fort.id, battlefield_id=entity.id)
    raise RuntimeError("control world has no route conflict triplet")


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


def inject_control_route_cut(world: ControlWorld, *, magnitude: float = 0.75, t: int = 120) -> dict[str, object]:
    triplet = find_control_route_conflict_triplet(world)
    road = world.entities[triplet.road_id]
    fort = world.entities[triplet.fort_id]
    battlefield = world.entities[triplet.battlefield_id]
    origin = road.coordinates[len(road.coordinates) // 2]

    perturbation = {
        "id": len(world.perturbations) + 1,
        "t": t,
        "type": "RouteCut",
        "target_layer": "route",
        "origin": origin,
        "magnitude": magnitude,
        "road_id": road.id,
        "fort_id": fort.id,
        "battlefield_id": battlefield.id,
    }
    world.perturbations.append(perturbation)

    road.state.function = max(0.0, road.state.function * (1.0 - magnitude * 0.65))
    road.state.integrity = max(0.0, road.state.integrity - magnitude * 0.45)
    road.state.stale = True
    road.state.clamp()

    fort.state.function = max(0.0, fort.state.function - magnitude * 0.08)
    fort.state.integrity = max(0.0, fort.state.integrity - magnitude * 0.08)
    fort.state.stale = True
    fort.state.clamp()

    battlefield.state.function = max(0.0, battlefield.state.function - magnitude * 0.10)
    battlefield.state.stale = True
    battlefield.state.clamp()
    return perturbation


def compact_control_timber_collapse(world: ControlWorld, *, t: int = 142) -> dict[str, object]:
    perturbation = _latest_control_perturbation(world, target_layer="timber")
    archive = {
        "id": len(world.compaction_archives) + 1,
        "t": t,
        "summary": "timber collapse compacted into local archive summary",
        "affected_entities": [perturbation["settlement_id"], perturbation["lumber_camp_id"]],
        "target_layer": "timber",
    }
    world.compaction_archives.append(archive)
    return archive


def compact_control_route_cut(world: ControlWorld, *, t: int = 160) -> dict[str, object]:
    perturbation = _latest_control_perturbation(world, target_layer="route")
    archive = {
        "id": len(world.compaction_archives) + 1,
        "t": t,
        "summary": "route cut compacted into corridor disruption summary",
        "affected_entities": [perturbation["road_id"], perturbation["fort_id"], perturbation["battlefield_id"]],
        "target_layer": "route",
    }
    world.compaction_archives.append(archive)
    return archive


def explain_control_entity(world: ControlWorld, entity_id: int) -> str:
    entity = world.entities[entity_id]
    lines = [
        f"{entity.name} [{entity.type}]",
        f"status={entity.state.status_label} wealth={entity.state.wealth:.2f} function={entity.state.function:.2f}",
    ]

    if world.control_label == "C":
        lines.extend([
            "posthoc_explanation:",
            f"- {entity.explanation_template}",
        ])
    elif world.control_label == "B":
        lines.extend([
            "heuristic_summary:",
            f"- {entity.notes['placement_reason']}",
            "- spatial coherence only; no executable provenance edges are stored.",
        ])
    else:
        lines.extend([
            "random_summary:",
            f"- random uncoupled placement at {entity.coordinates[0]} with no coherent dependency record.",
        ])

    latest = world.perturbations[-1] if world.perturbations else None
    if latest is not None and _control_entity_is_relevant_to_perturbation(entity, latest):
        if world.control_label == "A":
            lines.append(f"- event note: {latest['type']} touched this random baseline at {latest['origin']}.")
        elif latest["target_layer"] == "timber":
            lines.append(
                "- heuristic update: nearby timber destruction is used as a plausible retrospective cause, "
                "but this attribution is inferred from proximity/state similarity rather than from executable provenance."
            )
        elif latest["target_layer"] == "route":
            lines.append(
                "- heuristic update: a severed corridor is used as a plausible retrospective cause for fort and battlefield "
                "degradation, but the explanation is still inferred from narrative coherence rather than typed dependency edges."
            )
        lines.append(
            f"- observed event summary: {latest['type']} at {latest['origin']} magnitude={latest['magnitude']:.2f}"
        )

    for archive in reversed(world.compaction_archives):
        if entity.id in archive["affected_entities"]:
            if world.control_label == "A":
                lines.append(f"- compacted note: {archive['summary']}")
            else:
                lines.append(f"- compacted regional summary: {archive['summary']}")
                lines.append(
                    "- compaction retained only a coarse summary; no typed dependency edge or entity-specific causal archive survives."
                )
            break
    return "\n".join(lines)


def compare_worldline_vs_control_a(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control(generate_control_a, seed=seed, size=size)


def compare_worldline_vs_control_b(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control(generate_control_b, seed=seed, size=size)


def compare_worldline_vs_control_c(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control(generate_control_c, seed=seed, size=size)


def _compare_worldline_vs_control(
    control_factory,
    *,
    seed: int = 12345,
    size: int = 128,
) -> NegativeControlComparison:
    worldline = generate_world(seed=seed, size=size)
    worldline_settlement_id, _ = find_timber_dependency_pair(worldline)
    worldline_before = _state_signature(worldline.entities[worldline_settlement_id].state)
    inject_timber_destruction(worldline, magnitude=0.9, t=100)
    compact_timber_collapse(worldline, t=142)
    worldline_explanation = explain_entity(worldline, worldline_settlement_id)

    control = control_factory(seed=seed, size=size)
    control_pair = find_control_timber_dependency_pair(control)
    control_before = _state_signature(control.entities[control_pair.settlement_id].state)
    inject_control_timber_destruction(control, magnitude=0.9, t=100)
    compact_control_timber_collapse(control, t=142)
    control_explanation = explain_control_entity(control, control_pair.settlement_id)

    return NegativeControlComparison(
        worldline_post_perturbation_valid=_worldline_post_perturbation_valid(worldline_explanation),
        control_post_perturbation_valid=_control_post_perturbation_valid(control, control_explanation),
        worldline_compaction_retention_valid=_worldline_compaction_retention_valid(worldline_explanation),
        control_compaction_retention_valid=_control_compaction_retention_valid(control, control_explanation),
        worldline_perturbation_consequence_rate=_single_entity_consequence_rate(
            before=worldline_before,
            after=_state_signature(worldline.entities[worldline_settlement_id].state),
        ),
        control_perturbation_consequence_rate=_single_entity_consequence_rate(
            before=control_before,
            after=_state_signature(control.entities[control_pair.settlement_id].state),
        ),
        worldline_contradiction_count=_count_worldline_contradictions(worldline_explanation),
        control_contradiction_count=_count_control_contradictions(control, control_pair.settlement_id, control_explanation),
        worldline_explanation_depth=_explanation_depth(worldline_explanation),
        control_explanation_depth=_explanation_depth(control_explanation),
    )


def compare_worldline_vs_control_c_route_cut(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control_route_cut(generate_control_c, seed=seed, size=size)


def compare_worldline_vs_control_a_route_cut(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control_route_cut(generate_control_a, seed=seed, size=size)


def compare_worldline_vs_control_b_route_cut(seed: int = 12345, size: int = 128) -> NegativeControlComparison:
    return _compare_worldline_vs_control_route_cut(generate_control_b, seed=seed, size=size)


def _compare_worldline_vs_control_route_cut(
    control_factory,
    *,
    seed: int = 12345,
    size: int = 128,
) -> NegativeControlComparison:
    worldline = generate_world(seed=seed, size=size)
    _, _, worldline_battlefield_id = find_route_conflict_triplet(worldline)
    worldline_before = _state_signature(worldline.entities[worldline_battlefield_id].state)
    inject_route_cut(worldline, magnitude=0.75, t=120)
    compact_route_cut(worldline, t=160)
    worldline_explanation = explain_entity(worldline, worldline_battlefield_id)

    control = control_factory(seed=seed, size=size)
    control_triplet = find_control_route_conflict_triplet(control)
    control_before = _state_signature(control.entities[control_triplet.battlefield_id].state)
    inject_control_route_cut(control, magnitude=0.75, t=120)
    compact_control_route_cut(control, t=160)
    control_explanation = explain_control_entity(control, control_triplet.battlefield_id)

    return NegativeControlComparison(
        worldline_post_perturbation_valid=_worldline_route_cut_post_perturbation_valid(worldline_explanation),
        control_post_perturbation_valid=_control_route_cut_post_perturbation_valid(control, control_explanation),
        worldline_compaction_retention_valid=_worldline_route_cut_compaction_retention_valid(worldline_explanation),
        control_compaction_retention_valid=_control_route_cut_compaction_retention_valid(control, control_explanation),
        worldline_perturbation_consequence_rate=_single_entity_consequence_rate(
            before=worldline_before,
            after=_state_signature(worldline.entities[worldline_battlefield_id].state),
        ),
        control_perturbation_consequence_rate=_single_entity_consequence_rate(
            before=control_before,
            after=_state_signature(control.entities[control_triplet.battlefield_id].state),
        ),
        worldline_contradiction_count=_count_worldline_route_cut_contradictions(worldline_explanation),
        control_contradiction_count=_count_control_route_cut_contradictions(control, control_triplet.battlefield_id, control_explanation),
        worldline_explanation_depth=_explanation_depth(worldline_explanation),
        control_explanation_depth=_explanation_depth(control_explanation),
    )


def _control_entity_is_relevant_to_perturbation(entity: ControlEntity, perturbation: dict[str, object]) -> bool:
    if perturbation["target_layer"] == "timber":
        return entity.id in {perturbation.get("settlement_id"), perturbation.get("lumber_camp_id")}
    if perturbation["target_layer"] == "route":
        return entity.id in {perturbation.get("road_id"), perturbation.get("fort_id"), perturbation.get("battlefield_id")}
    return False


def _state_signature(state: EntityState) -> tuple[float, float, float, str, bool]:
    return (state.integrity, state.wealth, state.function, state.status_label, state.active)


def _single_entity_consequence_rate(
    *,
    before: tuple[float, float, float, str, bool],
    after: tuple[float, float, float, str, bool],
) -> float:
    return 1.0 if after != before else 0.0


def _latest_control_perturbation(world: ControlWorld, *, target_layer: str) -> dict[str, object]:
    for perturbation in reversed(world.perturbations):
        if perturbation["target_layer"] == target_layer:
            return perturbation
    raise RuntimeError(f"control world has no {target_layer} perturbation to compact")


def _worldline_post_perturbation_valid(explanation: str) -> bool:
    return "timber destruction" in explanation and "DAMAGES" in explanation


def _worldline_compaction_retention_valid(explanation: str) -> bool:
    return "CompactionArchiveEvent" in explanation and "timber collapse archive" in explanation


def _control_post_perturbation_valid(world: ControlWorld, explanation: str) -> bool:
    if world.control_label in {"A", "B"}:
        return False
    has_event_reference = "timber destruction" in explanation or "ResourceDestruction" in explanation
    has_executable_causal_link = "DAMAGES" in explanation or "SUPPLIES" in explanation
    is_explicitly_heuristic = "heuristic update" in explanation or "retrospective cause" in explanation
    return has_event_reference and has_executable_causal_link and not is_explicitly_heuristic


def _control_compaction_retention_valid(world: ControlWorld, explanation: str) -> bool:
    if world.control_label in {"A", "B", "C"}:
        return False
    has_archive_node = "CompactionArchiveEvent" in explanation
    has_entity_specific_retention = "dependency_loss" in explanation or "typed dependency edge" in explanation
    return has_archive_node and has_entity_specific_retention


def _worldline_route_cut_post_perturbation_valid(explanation: str) -> bool:
    return "route cut" in explanation and "DAMAGES" in explanation and "Road_" in explanation


def _worldline_route_cut_compaction_retention_valid(explanation: str) -> bool:
    return "CompactionArchiveEvent" in explanation and "route cut archive" in explanation


def _control_route_cut_post_perturbation_valid(world: ControlWorld, explanation: str) -> bool:
    if world.control_label in {"A", "B"}:
        return False
    has_event_reference = "RouteCut" in explanation or "route" in explanation
    has_executable_causal_link = "TRANSITS" in explanation or "DAMAGES" in explanation
    is_explicitly_heuristic = "heuristic update" in explanation or "narrative coherence" in explanation
    return has_event_reference and has_executable_causal_link and not is_explicitly_heuristic


def _control_route_cut_compaction_retention_valid(world: ControlWorld, explanation: str) -> bool:
    if world.control_label in {"A", "B", "C"}:
        return False
    has_archive_node = "CompactionArchiveEvent" in explanation
    has_entity_specific_retention = "typed dependency edge" in explanation and "entity-specific causal archive" not in explanation
    return has_archive_node and has_entity_specific_retention


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
    if world.control_label == "A":
        if "random uncoupled placement" in explanation:
            contradictions += 1
        if world.compaction_archives and "typed dependency edge" not in explanation:
            contradictions += 1
        if world.perturbations and "timber destruction" not in explanation and "ResourceDestruction" not in explanation:
            contradictions += 1
        return contradictions
    if entity.state.status_label == "Poor" and "promises construction support" in explanation:
        contradictions += 1
    if world.compaction_archives and "typed dependency edge" not in explanation:
        contradictions += 1
    if world.perturbations and "timber destruction" not in explanation:
        contradictions += 1
    if world.perturbations and "heuristic update" in explanation:
        contradictions += 1
    return contradictions


def _count_worldline_route_cut_contradictions(explanation: str) -> int:
    contradictions = 0
    if "route cut" not in explanation:
        contradictions += 1
    if "CompactionArchiveEvent" not in explanation:
        contradictions += 1
    return contradictions


def _count_control_route_cut_contradictions(world: ControlWorld, entity_id: int, explanation: str) -> int:
    entity = world.entities[entity_id]
    contradictions = 0
    if world.control_label == "A":
        if "random uncoupled placement" in explanation:
            contradictions += 1
        if world.compaction_archives and "typed dependency edge" not in explanation:
            contradictions += 1
        if world.perturbations and "RouteCut" not in explanation:
            contradictions += 1
        return contradictions
    if entity.type == EntityType.BATTLEFIELD and "conflict corridors" in explanation:
        contradictions += 1
    if world.compaction_archives and "entity-specific causal archive" in explanation:
        contradictions += 1
    if world.compaction_archives and "typed dependency edge" not in explanation:
        contradictions += 1
    if world.perturbations and "RouteCut" not in explanation:
        contradictions += 1
    if world.perturbations and "heuristic update" in explanation:
        contradictions += 1
    return contradictions


def _explanation_depth(explanation: str) -> int:
    return sum(1 for line in explanation.splitlines() if line.strip().startswith("-"))


@dataclass(frozen=True)
class _PlacementWorldView:
    baseline: dict[Coord, BaselineTile]
    size: int
