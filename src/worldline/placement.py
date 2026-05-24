"""Accountable entity placement for Worldline Projection.

Gate 2 starts here: entities are no longer merely hand-wired into the world. They
are selected from substrate-derived candidates and emit provenance as they are placed.
"""

from __future__ import annotations

from dataclasses import dataclass

from worldline.models import (
    EdgeType,
    Entity,
    EntityState,
    EntityType,
    NodeType,
    SettlementSubtype,
)
from worldline.world import World

Coord = tuple[int, int]


@dataclass(frozen=True)
class SettlementCandidate:
    coord: Coord
    subtype: SettlementSubtype
    score: float
    reasons: dict[str, float]


@dataclass(frozen=True)
class ResourceCandidate:
    coord: Coord
    resource: str
    score: float
    value: float


def place_core_entities(world: World, *, settlement_count: int = 5) -> None:
    """Place the first accountable entity set.

    Current Gate 2 coverage:

    - settlements
    - lumber camps
    - mines
    - roads connecting settlements to resource exploitation entities
    - forts placed on strategically meaningful road chokepoints
    """

    settlement_candidates = find_settlement_candidates(world)
    chosen_settlements = choose_spread_candidates(
        settlement_candidates, count=settlement_count, min_distance=max(8, world.size // 10)
    )
    if not chosen_settlements:
        raise RuntimeError("no accountable settlement candidates found")

    next_entity_id = 1
    road_specs: list[tuple[Entity, Entity, str, float]] = []
    for index, candidate in enumerate(chosen_settlements, start=1):
        settlement = _create_settlement(world, entity_id=next_entity_id, index=index, candidate=candidate)
        next_entity_id += 1

        lumber_candidate = best_resource_candidate_near(
            world, candidate.coord, resource="timber", max_distance=max(12, world.size // 8)
        )
        if lumber_candidate is not None and lumber_candidate.value > 0.25:
            lumber = _create_lumber_camp(world, entity_id=next_entity_id, settlement=settlement, candidate=lumber_candidate)
            next_entity_id += 1
            road_specs.append((settlement, lumber, "timber supply route", lumber_candidate.value))

        mine_candidate = best_mineral_candidate_near(world, candidate.coord, max_distance=max(18, world.size // 6))
        if mine_candidate is not None and mine_candidate.value > 0.35:
            mine = _create_mine(world, entity_id=next_entity_id, settlement=settlement, candidate=mine_candidate)
            next_entity_id += 1
            road_specs.append((settlement, mine, f"{mine_candidate.resource} supply route", mine_candidate.value))

    if not any(entity.type == EntityType.MINE for entity in world.entities.values()):
        settlement = first_settlement(world)
        candidate = best_global_mineral_candidate(world)
        mine = _create_mine(world, entity_id=next_entity_id, settlement=settlement, candidate=candidate)
        next_entity_id += 1
        road_specs.append((settlement, mine, f"{candidate.resource} fallback supply route", candidate.value))

    roads: list[Entity] = []
    for settlement, resource_entity, label, weight in road_specs:
        roads.append(
            _create_road(world, entity_id=next_entity_id, start=settlement, end=resource_entity, label=label, weight=weight)
        )
        next_entity_id += 1

    if roads:
        _create_fort(world, entity_id=next_entity_id, roads=roads)


def find_settlement_candidates(world: World) -> list[SettlementCandidate]:
    candidates: list[SettlementCandidate] = []
    for coord, tile in world.baseline.items():
        if tile.elevation <= -0.05:
            continue

        agrarian_score = tile.fertility * 0.55 + tile.water_flow * 0.35 + (1.0 - tile.slope) * 0.10
        mineral_score = max(tile.iron, tile.coal) * 0.55 + tile.water_flow * 0.20 + (1.0 - tile.slope) * 0.25
        trade_score = tile.water_flow * 0.45 + tile.fertility * 0.25 + max(tile.iron, tile.coal, tile.timber) * 0.30
        shrine_score = isolation_score(world, coord) * 0.55 + max(0.0, tile.elevation) * 0.25 + (1.0 - tile.fertility) * 0.20

        scored = [
            (agrarian_score, SettlementSubtype.AGRARIAN_VILLAGE),
            (mineral_score, SettlementSubtype.MINING_CAMP),
            (trade_score, SettlementSubtype.TRADE_TOWN),
            (shrine_score, SettlementSubtype.ISOLATED_SHRINE_SETTLEMENT),
        ]
        score, subtype = max(scored, key=lambda item: item[0])
        if score < 0.45:
            continue
        candidates.append(
            SettlementCandidate(
                coord=coord,
                subtype=subtype,
                score=score,
                reasons={
                    "fertility": tile.fertility,
                    "water_flow": tile.water_flow,
                    "timber": tile.timber,
                    "iron": tile.iron,
                    "coal": tile.coal,
                    "slope": tile.slope,
                    "elevation": tile.elevation,
                },
            )
        )
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates


def choose_spread_candidates(
    candidates: list[SettlementCandidate], *, count: int, min_distance: int
) -> list[SettlementCandidate]:
    chosen: list[SettlementCandidate] = []
    for candidate in candidates:
        if all(manhattan(candidate.coord, existing.coord) >= min_distance for existing in chosen):
            chosen.append(candidate)
        if len(chosen) >= count:
            break
    return chosen


def best_resource_candidate_near(
    world: World, origin: Coord, *, resource: str, max_distance: int
) -> ResourceCandidate | None:
    candidates: list[ResourceCandidate] = []
    for coord, tile in world.baseline.items():
        distance = manhattan(origin, coord)
        if distance > max_distance:
            continue
        value = getattr(tile, resource)
        if value <= 0.0:
            continue
        score = value - distance * 0.012
        candidates.append(ResourceCandidate(coord=coord, resource=resource, score=score, value=value))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate.score)


def best_mineral_candidate_near(world: World, origin: Coord, *, max_distance: int) -> ResourceCandidate | None:
    iron = best_resource_candidate_near(world, origin, resource="iron", max_distance=max_distance)
    coal = best_resource_candidate_near(world, origin, resource="coal", max_distance=max_distance)
    candidates = [candidate for candidate in [iron, coal] if candidate is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate.score)


def best_global_mineral_candidate(world: World) -> ResourceCandidate:
    candidates: list[ResourceCandidate] = []
    for coord, tile in world.baseline.items():
        if tile.iron > 0.0:
            candidates.append(ResourceCandidate(coord=coord, resource="iron", score=tile.iron, value=tile.iron))
        if tile.coal > 0.0:
            candidates.append(ResourceCandidate(coord=coord, resource="coal", score=tile.coal, value=tile.coal))
    if not candidates:
        raise RuntimeError("substrate produced no mineral candidates")
    return max(candidates, key=lambda candidate: candidate.score)


def first_settlement(world: World) -> Entity:
    for entity in world.entities.values():
        if entity.type == EntityType.SETTLEMENT:
            return entity
    raise RuntimeError("no settlement exists to anchor resource exploitation")


def _create_settlement(
    world: World, *, entity_id: int, index: int, candidate: SettlementCandidate
) -> Entity:
    tile = world.baseline[candidate.coord]
    water_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"water/fertility support for Settlement_{index:02d}",
        payload={"coord": candidate.coord, "water_flow": tile.water_flow, "fertility": tile.fertility},
    )
    subtype_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"subtype preconditions for {candidate.subtype}",
        payload=candidate.reasons,
    )
    settlement_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        f"Settlement_{index:02d} placed by accountable settlement scoring",
        entity_id=entity_id,
        payload={"coord": candidate.coord, "score": candidate.score, "subtype": candidate.subtype},
    )

    world.provenance.add_edge(water_node.id, settlement_node.id, EdgeType.LOCATES, weight=tile.fertility)
    world.provenance.add_edge(subtype_node.id, settlement_node.id, EdgeType.REQUIRES, weight=candidate.score)

    entity = Entity(
        id=entity_id,
        type=EntityType.SETTLEMENT,
        subtype=candidate.subtype,
        name=f"Settlement_{index:02d}",
        coordinates=[candidate.coord],
        state=EntityState(integrity=1.0, wealth=min(0.9, 0.35 + candidate.score * 0.45), function=1.0, active=True, status_label="Stable"),
        root_provenance_id=settlement_node.id,
    )
    entity.state.clamp()
    world.entities[entity.id] = entity
    return entity


def _create_lumber_camp(world: World, *, entity_id: int, settlement: Entity, candidate: ResourceCandidate) -> Entity:
    timber_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"timber field exploited by LumberCamp_{entity_id:02d}",
        payload={"coord": candidate.coord, "timber": candidate.value},
    )
    camp_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        f"LumberCamp_{entity_id:02d} placed near timber field",
        entity_id=entity_id,
        payload={"coord": candidate.coord, "score": candidate.score},
    )
    world.provenance.add_edge(timber_node.id, camp_node.id, EdgeType.ENABLES, weight=candidate.value)
    world.provenance.add_edge(camp_node.id, settlement.root_provenance_id, EdgeType.SUPPLIES, weight=candidate.value)

    entity = Entity(
        id=entity_id,
        type=EntityType.LUMBER_CAMP,
        subtype=None,
        name=f"LumberCamp_{entity_id:02d}",
        coordinates=[candidate.coord],
        state=EntityState(integrity=1.0, wealth=0.5, function=max(0.1, candidate.value), active=True),
        root_provenance_id=camp_node.id,
    )
    entity.state.clamp()
    world.entities[entity.id] = entity
    return entity


def _create_mine(world: World, *, entity_id: int, settlement: Entity, candidate: ResourceCandidate) -> Entity:
    mineral_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"{candidate.resource} deposit exploited by Mine_{entity_id:02d}",
        payload={"coord": candidate.coord, candidate.resource: candidate.value},
    )
    mine_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        f"Mine_{entity_id:02d} placed on {candidate.resource} deposit",
        entity_id=entity_id,
        payload={"coord": candidate.coord, "resource": candidate.resource, "score": candidate.score},
    )
    world.provenance.add_edge(mineral_node.id, mine_node.id, EdgeType.ENABLES, weight=candidate.value)
    world.provenance.add_edge(mine_node.id, settlement.root_provenance_id, EdgeType.SUPPLIES, weight=candidate.value)

    entity = Entity(
        id=entity_id,
        type=EntityType.MINE,
        subtype=candidate.resource,
        name=f"Mine_{entity_id:02d}",
        coordinates=[candidate.coord],
        state=EntityState(integrity=1.0, wealth=0.5, function=max(0.1, candidate.value), active=True),
        root_provenance_id=mine_node.id,
    )
    entity.state.clamp()
    world.entities[entity.id] = entity
    return entity


def _create_road(world: World, *, entity_id: int, start: Entity, end: Entity, label: str, weight: float) -> Entity:
    path = manhattan_path(start.coordinates[0], end.coordinates[0], size=world.size)
    route_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"transit corridor for {label}",
        payload={"start_entity": start.id, "end_entity": end.id, "path_length": len(path)},
    )
    road_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        f"Road_{entity_id:02d} carries {label}",
        entity_id=entity_id,
        payload={"start_entity": start.id, "end_entity": end.id, "path_length": len(path), "route_weight": weight},
    )
    world.provenance.add_edge(route_node.id, road_node.id, EdgeType.LOCATES, weight=max(0.1, 1.0 / max(1, len(path))))
    world.provenance.add_edge(road_node.id, start.root_provenance_id, EdgeType.TRANSITS, weight=weight, payload={"connected_entity": end.id})
    world.provenance.add_edge(road_node.id, end.root_provenance_id, EdgeType.TRANSITS, weight=weight, payload={"connected_entity": start.id})

    entity = Entity(
        id=entity_id,
        type=EntityType.ROAD,
        subtype="SupplyRoute",
        name=f"Road_{entity_id:02d}",
        coordinates=path,
        state=EntityState(integrity=1.0, wealth=0.0, function=1.0, active=True, status_label="Stable"),
        root_provenance_id=road_node.id,
    )
    entity.state.clamp()
    world.entities[entity.id] = entity
    return entity


def _create_fort(world: World, *, entity_id: int, roads: list[Entity]) -> Entity:
    road = max(roads, key=lambda candidate: _fort_road_score(world, candidate))
    fort_coord, chokepoint_score, midpoint_bias = _choose_fort_coord(world, road)
    road_node = world.provenance.nodes[road.root_provenance_id]
    start_entity = world.entities[road_node.payload["start_entity"]]
    end_entity = world.entities[road_node.payload["end_entity"]]
    route_weight = float(road_node.payload.get("route_weight", 0.0))
    road_score = _fort_road_score(world, road)

    pressure_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"route control pressure for {road.name}",
        payload={
            "road_entity": road.id,
            "path_length": len(road.coordinates),
            "route_weight": route_weight,
            "start_entity": start_entity.id,
            "end_entity": end_entity.id,
            "strategic_score": road_score,
        },
    )
    terrain_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        f"defensible road position on {road.name}",
        payload={
            "coord": fort_coord,
            "road_entity": road.id,
            "chokepoint_score": chokepoint_score,
            "midpoint_bias": midpoint_bias,
        },
    )
    fort_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        f"Fort_{entity_id:02d} controls {road.name}",
        entity_id=entity_id,
        payload={
            "coord": fort_coord,
            "road_entity": road.id,
            "strategic_score": road_score,
            "chokepoint_score": chokepoint_score,
        },
    )

    world.provenance.add_edge(
        road.root_provenance_id,
        fort_node.id,
        EdgeType.ENABLES,
        weight=max(0.1, route_weight + len(road.coordinates) / max(8.0, world.size / 2)),
        payload={"role": "controlled_route", "road_entity": road.id},
    )
    world.provenance.add_edge(
        terrain_node.id,
        fort_node.id,
        EdgeType.LOCATES,
        weight=max(0.1, chokepoint_score),
        payload={"coord": fort_coord},
    )
    world.provenance.add_edge(
        pressure_node.id,
        fort_node.id,
        EdgeType.REQUIRES,
        weight=max(0.1, road_score),
    )

    entity = Entity(
        id=entity_id,
        type=EntityType.FORT,
        subtype="RouteControl",
        name=f"Fort_{entity_id:02d}",
        coordinates=[fort_coord],
        state=EntityState(
            integrity=1.0,
            wealth=min(0.8, 0.25 + route_weight * 0.45),
            function=min(1.0, 0.4 + chokepoint_score * 0.6),
            active=True,
            status_label="Stable",
        ),
        root_provenance_id=fort_node.id,
    )
    entity.state.clamp()
    world.entities[entity.id] = entity
    return entity


def _fort_road_score(world: World, road: Entity) -> float:
    road_node = world.provenance.nodes[road.root_provenance_id]
    start_entity = world.entities[road_node.payload["start_entity"]]
    end_entity = world.entities[road_node.payload["end_entity"]]
    length_score = len(road.coordinates) / max(6.0, world.size / 3)
    route_weight = float(road_node.payload.get("route_weight", 0.0))
    resource_bonus = 0.25 if end_entity.type in {EntityType.MINE, EntityType.LUMBER_CAMP} else 0.0
    settlement_bonus = 0.10 if start_entity.type == EntityType.SETTLEMENT else 0.0
    midpoint_coord = road.coordinates[len(road.coordinates) // 2]
    tile = world.baseline[midpoint_coord]
    terrain_bonus = max(0.0, tile.slope * 0.35 + tile.elevation * 0.20)
    return route_weight + length_score + resource_bonus + settlement_bonus + terrain_bonus


def _choose_fort_coord(world: World, road: Entity) -> tuple[Coord, float, float]:
    if len(road.coordinates) <= 2:
        coord = road.coordinates[len(road.coordinates) // 2]
        return coord, 0.1, 1.0

    midpoint_index = len(road.coordinates) // 2
    interior = list(enumerate(road.coordinates[1:-1], start=1))
    best_index, best_coord = max(
        interior,
        key=lambda item: _fort_coord_score(world, road, item[0], midpoint_index),
    )
    tile = world.baseline[best_coord]
    chokepoint_score = max(0.1, tile.slope * 0.6 + tile.elevation * 0.4)
    midpoint_bias = 1.0 - abs(best_index - midpoint_index) / max(1, midpoint_index)
    return best_coord, chokepoint_score, max(0.0, midpoint_bias)


def _fort_coord_score(world: World, road: Entity, index: int, midpoint_index: int) -> float:
    coord = road.coordinates[index]
    tile = world.baseline[coord]
    endpoint_distance = min(index, len(road.coordinates) - 1 - index)
    distance_score = min(1.0, endpoint_distance / max(1.0, len(road.coordinates) / 4))
    midpoint_bias = 1.0 - abs(index - midpoint_index) / max(1, midpoint_index)
    terrain_score = tile.slope * 0.45 + tile.elevation * 0.25 + (1.0 - tile.water_flow) * 0.10
    return terrain_score + distance_score * 0.35 + midpoint_bias * 0.20


def manhattan_path(start: Coord, end: Coord, *, size: int) -> list[Coord]:
    x, y = start
    ex, ey = end
    path = [(x, y)]
    step_x = 1 if ex >= x else -1
    while x != ex:
        x += step_x
        path.append((x, y))
    step_y = 1 if ey >= y else -1
    while y != ey:
        y += step_y
        path.append((x, y))
    if len(path) == 1:
        nx = x + 1 if x + 1 < size else x - 1
        path.append((nx, y))
    return path


def isolation_score(world: World, coord: Coord) -> float:
    tile = world.baseline[coord]
    return max(0.0, min(1.0, tile.elevation * 0.6 + (1.0 - tile.water_flow) * 0.4))


def manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
