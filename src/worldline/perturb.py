"""Perturbation and resolver skeleton for the first proof scenario."""

from __future__ import annotations

from dataclasses import dataclass

from worldline.models import (
    EdgeType,
    Entity,
    EntityType,
    LocalBaselinePatch,
    NodeType,
    PatchTileDelta,
    Perturbation,
    PerturbationType,
)
from worldline.world import World


@dataclass(frozen=True)
class PropagationImpact:
    source_entity_id: int
    target_entity_id: int
    edge_type: EdgeType
    intensity: float


def find_timber_dependency_pair(world: World) -> tuple[int, int]:
    """Return (settlement_id, lumber_camp_id) for the strongest current timber dependency."""

    best: tuple[float, int, int] | None = None
    for edge in world.provenance.edges.values():
        if edge.edge_type != EdgeType.SUPPLIES:
            continue
        source = world.provenance.nodes[edge.source_node_id]
        target = world.provenance.nodes[edge.target_node_id]
        if source.entity_id is None or target.entity_id is None:
            continue
        source_entity = world.entities[source.entity_id]
        target_entity = world.entities[target.entity_id]
        if source_entity.type == EntityType.LUMBER_CAMP and target_entity.type == EntityType.SETTLEMENT:
            candidate = (edge.weight, target_entity.id, source_entity.id)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None:
        raise RuntimeError("no settlement with lumber-camp dependency found")
    return best[1], best[2]


def inject_timber_destruction(world: World, *, magnitude: float = 0.9, t: int = 100) -> Perturbation:
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    lumber = world.entities[lumber_id]
    origin = lumber.coordinates[0]

    perturbation = Perturbation(
        id=len(world.perturbations) + 1,
        t=t,
        type=PerturbationType.RESOURCE_DESTRUCTION,
        origin=origin,
        radius=5,
        magnitude=magnitude,
        target_layer="timber",
        payload={"region_id": "demo_timber_region", "lumber_camp_id": lumber_id, "settlement_id": settlement_id},
    )
    world.perturbations[perturbation.id] = perturbation

    perturb_node = world.provenance.add_node(
        NodeType.PERTURBATION_EVENT,
        "timber destruction near lumber dependency",
        event_id=perturbation.id,
        payload={"magnitude": magnitude, "target_layer": "timber", "origin": origin},
    )

    impacted_entities = _find_direct_resource_impacts(world, perturbation)
    if not impacted_entities:
        raise RuntimeError("timber perturbation did not match any accountable resource dependency")

    frontier = []
    for entity in impacted_entities:
        _apply_direct_resource_damage(world, entity=entity, perturbation=perturbation, perturb_node_id=perturb_node.id)
        frontier.append((entity.id, perturbation.magnitude))

    for impact in _propagate_damage(world, frontier=frontier):
        _apply_propagated_damage(world, impact=impact)

    return perturbation


def find_route_conflict_triplet(world: World) -> tuple[int, int, int]:
    """Return (road_id, fort_id, battlefield_id) for a battlefield anchored to a routed conflict."""

    best: tuple[float, int, int, int] | None = None
    for entity in world.entities.values():
        if entity.type != EntityType.BATTLEFIELD:
            continue

        road_id: int | None = None
        fort_id: int | None = None
        conflict_score = 0.0
        for edge, parent in world.provenance.parents_of(entity.root_provenance_id):
            if edge.edge_type == EdgeType.ENABLES and parent.entity_id is not None:
                parent_entity = world.entities[parent.entity_id]
                if parent_entity.type == EntityType.ROAD:
                    road_id = parent_entity.id
                    conflict_score = max(conflict_score, edge.weight)
            elif edge.edge_type == EdgeType.CAUSES:
                fort_id = parent.payload.get("fort_entity")
                conflict_score = max(conflict_score, edge.weight)

        if road_id is None or fort_id is None:
            continue

        candidate = (conflict_score, road_id, fort_id, entity.id)
        if best is None or candidate > best:
            best = candidate

    if best is None:
        raise RuntimeError("no battlefield with accountable route conflict found")
    return best[1], best[2], best[3]


def inject_route_cut(world: World, *, magnitude: float = 0.75, t: int = 120) -> Perturbation:
    """Damage a road-backed conflict corridor and propagate the loss through transit dependencies."""

    road_id, fort_id, battlefield_id = find_route_conflict_triplet(world)
    road = world.entities[road_id]
    cut_index = len(road.coordinates) // 2
    origin = road.coordinates[cut_index]

    perturbation = Perturbation(
        id=len(world.perturbations) + 1,
        t=t,
        type=PerturbationType.ROUTE_CUT,
        origin=origin,
        radius=0,
        magnitude=magnitude,
        target_layer="route",
        target_entity_id=road_id,
        payload={"road_id": road_id, "fort_id": fort_id, "battlefield_id": battlefield_id, "cut_index": cut_index},
    )
    world.perturbations[perturbation.id] = perturbation

    perturb_node = world.provenance.add_node(
        NodeType.PERTURBATION_EVENT,
        f"route cut on {road.name}",
        event_id=perturbation.id,
        payload={"magnitude": magnitude, "target_layer": "route", "origin": origin, "road_entity": road_id},
    )

    _apply_direct_entity_damage(world, entity=road, perturbation=perturbation, perturb_node_id=perturb_node.id)
    for impact in _propagate_damage(world, frontier=[(road.id, perturbation.magnitude)]):
        _apply_propagated_damage(world, impact=impact)

    return perturbation


def _find_direct_resource_impacts(world: World, perturbation: Perturbation) -> list[Entity]:
    impacted: list[Entity] = []
    for entity in world.entities.values():
        if perturbation.target_layer == "timber" and entity.type != EntityType.LUMBER_CAMP:
            continue
        if perturbation.target_layer in {"iron", "coal"} and entity.type != EntityType.MINE:
            continue
        if not any(_coord_in_radius(perturbation.origin, coord, perturbation.radius) for coord in entity.coordinates):
            continue
        if _entity_has_matching_substrate_precondition(world, entity, perturbation):
            impacted.append(entity)
    return impacted


def _entity_has_matching_substrate_precondition(world: World, entity: Entity, perturbation: Perturbation) -> bool:
    for edge, parent in world.provenance.parents_of(entity.root_provenance_id):
        if parent.node_type != NodeType.SUBSTRATE_PRECONDITION:
            continue
        coord = parent.payload.get("coord")
        if coord != perturbation.origin:
            continue
        if perturbation.target_layer not in parent.payload:
            continue
        if edge.edge_type not in {EdgeType.ENABLES, EdgeType.LOCATES, EdgeType.REQUIRES}:
            continue
        return True
    return False


def _apply_direct_resource_damage(
    world: World,
    *,
    entity: Entity,
    perturbation: Perturbation,
    perturb_node_id: int,
) -> None:
    old_function = entity.state.function
    old_integrity = entity.state.integrity
    entity.state.function = max(0.0, entity.state.function * (1.0 - perturbation.magnitude * 0.83))
    entity.state.integrity = max(0.0, entity.state.integrity - perturbation.magnitude * 0.25)
    entity.state.stale = True
    entity.state.clamp()

    world.provenance.add_edge(
        perturb_node_id,
        entity.root_provenance_id,
        EdgeType.DAMAGES,
        weight=perturbation.magnitude,
        payload={
            "target_layer": perturbation.target_layer,
            "old_function": old_function,
            "new_function": entity.state.function,
            "old_integrity": old_integrity,
            "new_integrity": entity.state.integrity,
        },
    )


def _apply_direct_entity_damage(
    world: World,
    *,
    entity: Entity,
    perturbation: Perturbation,
    perturb_node_id: int,
) -> None:
    old_function = entity.state.function
    old_integrity = entity.state.integrity
    entity.state.function = max(0.0, entity.state.function * (1.0 - perturbation.magnitude * 0.65))
    entity.state.integrity = max(0.0, entity.state.integrity - perturbation.magnitude * 0.45)
    entity.state.stale = True
    entity.state.clamp()

    world.provenance.add_edge(
        perturb_node_id,
        entity.root_provenance_id,
        EdgeType.DAMAGES,
        weight=perturbation.magnitude,
        payload={
            "target_entity": entity.id,
            "target_layer": perturbation.target_layer,
            "old_function": old_function,
            "new_function": entity.state.function,
            "old_integrity": old_integrity,
            "new_integrity": entity.state.integrity,
        },
    )


def _propagate_damage(world: World, *, frontier: list[tuple[int, float]]) -> list[PropagationImpact]:
    queue = list(frontier)
    impacts: list[PropagationImpact] = []
    best_seen: dict[tuple[int, int], float] = {}

    while queue:
        source_entity_id, source_intensity = queue.pop(0)
        source_entity = world.entities[source_entity_id]
        for edge, child in world.provenance.children_of(source_entity.root_provenance_id):
            if child.entity_id is None:
                continue
            propagated = _edge_propagation_intensity(edge_type=edge.edge_type, edge_weight=edge.weight, source_intensity=source_intensity)
            if propagated <= 0.0:
                continue
            key = (source_entity_id, child.entity_id)
            if propagated <= best_seen.get(key, 0.0):
                continue
            best_seen[key] = propagated
            impact = PropagationImpact(
                source_entity_id=source_entity_id,
                target_entity_id=child.entity_id,
                edge_type=edge.edge_type,
                intensity=propagated,
            )
            impacts.append(impact)
            queue.append((child.entity_id, propagated))
    return impacts


def _edge_propagation_intensity(*, edge_type: EdgeType, edge_weight: float, source_intensity: float) -> float:
    if edge_type == EdgeType.SUPPLIES:
        return source_intensity * edge_weight
    if edge_type == EdgeType.ENABLES:
        return source_intensity * edge_weight * 0.65
    if edge_type == EdgeType.TRANSITS:
        return source_intensity * edge_weight * 0.30
    if edge_type == EdgeType.REQUIRES:
        return source_intensity * edge_weight * 0.80
    return 0.0


def _apply_propagated_damage(world: World, *, impact: PropagationImpact) -> None:
    source_entity = world.entities[impact.source_entity_id]
    target_entity = world.entities[impact.target_entity_id]
    intensity = max(0.0, min(1.0, impact.intensity))

    old_wealth = target_entity.state.wealth
    old_function = target_entity.state.function
    old_integrity = target_entity.state.integrity

    if impact.edge_type == EdgeType.SUPPLIES:
        target_entity.state.wealth = max(0.0, target_entity.state.wealth - intensity * 0.40)
        target_entity.state.function = max(0.0, target_entity.state.function - intensity * 0.20)
    elif impact.edge_type == EdgeType.TRANSITS:
        target_entity.state.function = max(0.0, target_entity.state.function - intensity * 0.10)
    elif impact.edge_type == EdgeType.ENABLES:
        target_entity.state.function = max(0.0, target_entity.state.function - intensity * 0.16)
    elif impact.edge_type == EdgeType.REQUIRES:
        target_entity.state.integrity = max(0.0, target_entity.state.integrity - intensity * 0.12)
        target_entity.state.function = max(0.0, target_entity.state.function - intensity * 0.12)
    else:
        return

    target_entity.state.stale = True
    target_entity.state.clamp()

    world.provenance.add_edge(
        source_entity.root_provenance_id,
        target_entity.root_provenance_id,
        EdgeType.DAMAGES,
        weight=intensity,
        payload={
            "propagated_via": impact.edge_type,
            "source_entity": source_entity.id,
            "old_wealth": old_wealth,
            "new_wealth": target_entity.state.wealth,
            "old_function": old_function,
            "new_function": target_entity.state.function,
            "old_integrity": old_integrity,
            "new_integrity": target_entity.state.integrity,
        },
    )


def _coord_in_radius(origin: tuple[int, int], coord: tuple[int, int], radius: int) -> bool:
    return abs(origin[0] - coord[0]) + abs(origin[1] - coord[1]) <= radius


def compact_timber_collapse(world: World, *, t: int = 142) -> int:
    """Create a compaction archive node without erasing causal explanation."""

    settlement_id, lumber_id = find_timber_dependency_pair(world)
    settlement = world.entities[settlement_id]
    lumber = world.entities[lumber_id]
    source_perturbations = list(world.perturbations.values())
    archive_node = world.provenance.add_node(
        NodeType.COMPACTION_ARCHIVE_EVENT,
        "timber collapse archive for generated lumber dependency",
        payload={
            "event_type": "TimberCollapse",
            "time_range": [100, t],
            "spatial_scope": "demo_timber_region",
            "source_perturbation_ids": [perturbation.id for perturbation in source_perturbations],
            "affected_entities": {
                settlement.name: {
                    "dependency_loss": 0.90,
                    "wealth": settlement.state.wealth,
                    "function": settlement.state.function,
                },
                lumber.name: {
                    "dependency_loss": 0.90,
                    "function": lumber.state.function,
                },
            },
            "causal_sequence": [
                [100, "ResourceDestruction", "timber field damaged"],
                [115, "LumberCamp function collapse", "timber extraction degraded"],
                [142, "Settlement degradation", "wealth/function declined"],
            ],
        },
    )
    world.provenance.add_edge(
        archive_node.id,
        settlement.root_provenance_id,
        EdgeType.CAUSES,
        weight=0.9,
        payload={"compacted": True, "meaning_preserved": True},
    )
    world.provenance.add_edge(
        archive_node.id,
        lumber.root_provenance_id,
        EdgeType.CAUSES,
        weight=0.9,
        payload={"compacted": True, "meaning_preserved": True},
    )

    patch_id = len(world.patches) + 1
    tile_overrides = {}
    for perturbation in source_perturbations:
        if perturbation.target_layer != "timber":
            continue
        tile_overrides[perturbation.origin] = PatchTileDelta(timber_delta=-perturbation.magnitude)
    world.patches[patch_id] = LocalBaselinePatch(
        id=patch_id,
        region_id="demo_timber_region",
        created_at_t=t,
        tile_overrides=tile_overrides,
        archive_event_ids=[archive_node.id],
    )
    return archive_node.id
