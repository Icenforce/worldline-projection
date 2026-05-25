"""Perturbation and resolver logic for executable consequence propagation."""

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


@dataclass(frozen=True)
class CompactedConsequenceBundle:
    archive_node_id: int
    patch_id: int
    patch_ids: tuple[int, ...]
    source_perturbation_ids: tuple[int, ...]
    affected_entity_ids: tuple[int, ...]


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
            propagated = _edge_propagation_intensity(
                edge_type=edge.edge_type,
                edge_weight=edge.weight,
                source_intensity=source_intensity,
            )
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


def compact_perturbation_consequences(
    world: World,
    *,
    perturbation_ids: list[int] | None = None,
    t: int = 142,
) -> CompactedConsequenceBundle:
    """Archive perturbation consequences without erasing causal explanation."""

    source_perturbations = _resolve_source_perturbations(world, perturbation_ids)
    perturbation_groups = _collect_damage_groups(world, source_perturbations)
    all_damage_edges = _flatten_group_edges(perturbation_groups)
    if not all_damage_edges:
        raise RuntimeError("no direct perturbation damage edges found for compaction")

    affected_entity_ids = _affected_entity_ids(world, all_damage_edges)
    archive_label = _archive_label(world, source_perturbations)
    archive_payload = {
        "event_type": _archive_event_type(source_perturbations),
        "time_range": [min(perturbation.t for perturbation in source_perturbations), t],
        "spatial_scope": _spatial_scope(source_perturbations),
        "source_perturbation_ids": [perturbation.id for perturbation in source_perturbations],
        "affected_entity_ids": affected_entity_ids,
        "affected_entity_groups": _affected_entity_groups(world, perturbation_groups),
        "affected_entities": _affected_entities_payload(world, affected_entity_ids, all_damage_edges),
        "source_groups": _source_groups_payload(world, source_perturbations, perturbation_groups, t=t),
        "typed_provenance_links": _typed_provenance_links(all_damage_edges),
        "causal_sequence": _causal_sequence(world, source_perturbations, perturbation_groups, t=t),
    }
    archive_node = world.provenance.add_node(NodeType.COMPACTION_ARCHIVE_EVENT, archive_label, payload=archive_payload)

    for entity_id in affected_entity_ids:
        entity = world.entities[entity_id]
        related_edges = [edge for edge in all_damage_edges if edge.target_node_id == entity.root_provenance_id]
        link_types = sorted(
            {
                str(edge.payload.get("propagated_via", EdgeType.DAMAGES))
                for edge in related_edges
            }
        )
        state_deltas = [
            {
                key: value
                for key, value in edge.payload.items()
                if key.startswith("old_") or key.startswith("new_")
            }
            for edge in related_edges
        ]
        world.provenance.add_edge(
            archive_node.id,
            entity.root_provenance_id,
            EdgeType.CAUSES,
            weight=max((edge.weight for edge in related_edges), default=0.1),
            payload={
                "compacted": True,
                "meaning_preserved": True,
                "source_perturbation_ids": [perturbation.id for perturbation in source_perturbations],
                "affected_entity_id": entity_id,
                "preserved_link_types": link_types,
                "state_deltas": state_deltas,
            },
        )

    patch_ids = _create_compaction_patches(world, source_perturbations, archive_node.id, t=t)
    return CompactedConsequenceBundle(
        archive_node_id=archive_node.id,
        patch_id=patch_ids[0],
        patch_ids=tuple(patch_ids),
        source_perturbation_ids=tuple(perturbation.id for perturbation in source_perturbations),
        affected_entity_ids=tuple(affected_entity_ids),
    )


def compact_timber_collapse(world: World, *, t: int = 142) -> int:
    bundle = compact_perturbation_consequences(
        world,
        perturbation_ids=[perturbation.id for perturbation in world.perturbations.values() if perturbation.target_layer == "timber"],
        t=t,
    )
    return bundle.archive_node_id


def compact_route_cut(world: World, *, t: int = 142) -> int:
    bundle = compact_perturbation_consequences(
        world,
        perturbation_ids=[perturbation.id for perturbation in world.perturbations.values() if perturbation.target_layer == "route"],
        t=t,
    )
    return bundle.archive_node_id


def _resolve_source_perturbations(world: World, perturbation_ids: list[int] | None) -> list[Perturbation]:
    if perturbation_ids is None:
        perturbations = list(world.perturbations.values())
    else:
        perturbations = [world.perturbations[perturbation_id] for perturbation_id in perturbation_ids]
    if not perturbations:
        raise RuntimeError("no perturbations available for compaction")
    return perturbations


def _collect_damage_groups(
    world: World,
    source_perturbations: list[Perturbation],
) -> dict[int, list]:
    perturbation_event_node_ids = {
        node.event_id: node.id
        for node in world.provenance.nodes.values()
        if node.node_type == NodeType.PERTURBATION_EVENT and node.event_id in {perturbation.id for perturbation in source_perturbations}
    }
    groups: dict[int, list] = {}
    for perturbation in source_perturbations:
        perturbation_event_node_id = perturbation_event_node_ids.get(perturbation.id)
        if perturbation_event_node_id is None:
            continue
        direct_damage_edges = [
            edge
            for edge in world.provenance.edges.values()
            if edge.edge_type == EdgeType.DAMAGES and edge.source_node_id == perturbation_event_node_id
        ]
        all_damage_edges = list(direct_damage_edges)
        queue = [edge.target_node_id for edge in direct_damage_edges]
        seen_targets = set(queue)
        seen_edges = {edge.id for edge in direct_damage_edges}
        while queue:
            source_node_id = queue.pop(0)
            for edge in world.provenance.edges.values():
                if edge.edge_type != EdgeType.DAMAGES or edge.source_node_id != source_node_id:
                    continue
                if edge.id not in seen_edges:
                    seen_edges.add(edge.id)
                    all_damage_edges.append(edge)
                if edge.target_node_id not in seen_targets:
                    seen_targets.add(edge.target_node_id)
                    queue.append(edge.target_node_id)
        groups[perturbation.id] = all_damage_edges
    return groups


def _flatten_group_edges(perturbation_groups: dict[int, list]) -> list:
    all_edges: list = []
    seen_edge_ids: set[int] = set()
    for edges in perturbation_groups.values():
        for edge in edges:
            if edge.id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge.id)
            all_edges.append(edge)
    return all_edges


def _affected_entity_ids(world: World, damage_edges: list) -> list[int]:
    affected: list[int] = []
    for edge in damage_edges:
        target = world.provenance.nodes[edge.target_node_id]
        if target.entity_id is None:
            continue
        if target.entity_id not in affected:
            affected.append(target.entity_id)
    return affected


def _archive_label(world: World, source_perturbations: list[Perturbation]) -> str:
    first = source_perturbations[0]
    if first.target_layer == "timber":
        _, lumber_id = find_timber_dependency_pair(world)
        lumber = world.entities[lumber_id]
        return f"timber collapse archive for generated {lumber.name.lower()} dependency"
    if first.target_layer == "route":
        road_id = first.payload["road_id"]
        road = world.entities[road_id]
        return f"route cut archive for {road.name} conflict corridor"
    return f"compaction archive for {first.target_layer} consequence bundle"


def _archive_event_type(source_perturbations: list[Perturbation]) -> str:
    if len(source_perturbations) == 1:
        perturbation = source_perturbations[0]
        if perturbation.target_layer == "timber":
            return "TimberCollapse"
        if perturbation.target_layer == "route":
            return "RouteCut"
        return str(perturbation.type)
    return "CompositeConsequenceBundle"


def _spatial_scope(source_perturbations: list[Perturbation]) -> str:
    first = source_perturbations[0]
    if "region_id" in first.payload:
        return str(first.payload["region_id"])
    if first.target_layer == "route":
        return f"road_entity_{first.payload['road_id']}"
    return f"perturbation_origin_{first.origin[0]}_{first.origin[1]}"


def _affected_entities_payload(world: World, affected_entity_ids: list[int], damage_edges: list) -> dict[str, dict]:
    payload: dict[str, dict] = {}
    for entity_id in affected_entity_ids:
        entity = world.entities[entity_id]
        related_edges = [edge for edge in damage_edges if edge.target_node_id == entity.root_provenance_id]
        payload[str(entity_id)] = {
            "entity_id": entity.id,
            "name": entity.name,
            "type": str(entity.type),
            "final_state": {
                "integrity": entity.state.integrity,
                "wealth": entity.state.wealth,
                "function": entity.state.function,
                "status_label": entity.state.status_label,
            },
            "state_deltas": [
                {
                    key: value
                    for key, value in edge.payload.items()
                    if key.startswith("old_") or key.startswith("new_")
                }
                for edge in related_edges
            ],
        }
    return payload


def _typed_provenance_links(damage_edges: list, *, perturbation_id: int | None = None) -> list[dict]:
    links: list[dict] = []
    for edge in damage_edges:
        link = {
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "edge_type": str(edge.edge_type),
            "weight": edge.weight,
            "payload": dict(edge.payload),
        }
        if perturbation_id is not None:
            link["source_perturbation_id"] = perturbation_id
        links.append(link)
    return links


def _affected_entity_groups(world: World, perturbation_groups: dict[int, list]) -> dict[str, list[int]]:
    return {
        str(perturbation_id): _affected_entity_ids(world, edges)
        for perturbation_id, edges in perturbation_groups.items()
    }


def _source_groups_payload(
    world: World,
    source_perturbations: list[Perturbation],
    perturbation_groups: dict[int, list],
    *,
    t: int,
) -> list[dict]:
    payload: list[dict] = []
    for perturbation in sorted(source_perturbations, key=lambda item: item.t):
        group_edges = perturbation_groups.get(perturbation.id, [])
        affected_ids = _affected_entity_ids(world, group_edges)
        payload.append(
            {
                "source_perturbation_id": perturbation.id,
                "event_type": str(perturbation.type),
                "target_layer": perturbation.target_layer,
                "origin": perturbation.origin,
                "affected_entity_ids": affected_ids,
                "affected_entities": _affected_entities_payload(world, affected_ids, group_edges),
                "typed_provenance_links": _typed_provenance_links(group_edges, perturbation_id=perturbation.id),
                "causal_sequence": _causal_sequence(world, [perturbation], {perturbation.id: group_edges}, t=t),
            }
        )
    return payload


def _causal_sequence(
    world: World,
    source_perturbations: list[Perturbation],
    perturbation_groups: dict[int, list],
    *,
    t: int,
) -> list[list]:
    sequence: list[list] = []
    for perturbation in sorted(source_perturbations, key=lambda item: item.t):
        sequence.append(
            [
                perturbation.t,
                str(perturbation.type),
                perturbation.id,
                f"{perturbation.target_layer} damaged at {perturbation.origin}",
            ]
        )
        for edge in perturbation_groups.get(perturbation.id, []):
            target = world.provenance.nodes[edge.target_node_id]
            if target.entity_id is None:
                continue
            entity = world.entities[target.entity_id]
            propagated_via = edge.payload.get("propagated_via", EdgeType.DAMAGES)
            sequence.append(
                [
                    t,
                    str(propagated_via),
                    perturbation.id,
                    f"{entity.name} changed under {propagated_via}",
                ]
            )
    return sequence


def _create_compaction_patches(
    world: World,
    source_perturbations: list[Perturbation],
    archive_node_id: int,
    *,
    t: int,
) -> list[int]:
    patch_ids: list[int] = []
    for perturbation in source_perturbations:
        patch_id = len(world.patches) + 1
        if perturbation.target_layer == "timber":
            tile_overrides = {perturbation.origin: PatchTileDelta(timber_delta=-perturbation.magnitude)}
        elif perturbation.target_layer == "iron":
            tile_overrides = {perturbation.origin: PatchTileDelta(iron_delta=-perturbation.magnitude)}
        elif perturbation.target_layer == "coal":
            tile_overrides = {perturbation.origin: PatchTileDelta(coal_delta=-perturbation.magnitude)}
        else:
            tile_overrides = {perturbation.origin: PatchTileDelta()}

        world.patches[patch_id] = LocalBaselinePatch(
            id=patch_id,
            region_id=_spatial_scope([perturbation]),
            created_at_t=t,
            tile_overrides=tile_overrides,
            archive_event_ids=[archive_node_id],
        )
        patch_ids.append(patch_id)
    return patch_ids
