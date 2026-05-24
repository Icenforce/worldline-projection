"""Deterministic world generator for Worldline Projection."""

from __future__ import annotations

from worldline.models import (
    EdgeType,
    Entity,
    EntityState,
    EntityType,
    NodeType,
    SettlementSubtype,
)
from worldline.substrate import generate_substrate
from worldline.world import World


def generate_world(seed: int = 12345, size: int = 128) -> World:
    world = World(seed=seed, size=size)
    world.baseline = generate_substrate(seed=seed, size=size)
    _add_timber_demo_entities(world)
    return world


def _add_timber_demo_entities(world: World) -> None:
    """Create a deliberately small causal chain for the first proof scenario.

    This remains demo-specific until Gate 2 replaces it with accountable placement logic.
    The natural timber and water fields now come from the real substrate generator.
    """

    settlement_id = 1
    lumber_id = 2
    settlement_coord = _best_settlement_coord(world)
    lumber_coord = _best_lumber_coord_near(world, settlement_coord)
    timber_value = world.baseline[lumber_coord].timber
    settlement_tile = world.baseline[settlement_coord]

    timber_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        "high-timber forest field near demo settlement",
        payload={
            "field": "timber",
            "coord": lumber_coord,
            "value": timber_value,
            "biome": world.baseline[lumber_coord].biome,
        },
    )
    water_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        "water-supported fertile settlement site",
        payload={
            "field": "water_flow/fertility",
            "coord": settlement_coord,
            "water_flow": settlement_tile.water_flow,
            "fertility": settlement_tile.fertility,
        },
    )
    lumber_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        "LumberCamp_02 exploits nearby timber",
        entity_id=lumber_id,
    )
    settlement_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        "Settlement_01 depends on timber supply and fertile water access",
        entity_id=settlement_id,
    )

    world.provenance.add_edge(
        timber_node.id,
        lumber_node.id,
        EdgeType.ENABLES,
        weight=max(0.1, timber_value),
        payload={"coord": lumber_coord},
    )
    world.provenance.add_edge(lumber_node.id, settlement_node.id, EdgeType.SUPPLIES, weight=0.9)
    world.provenance.add_edge(
        water_node.id,
        settlement_node.id,
        EdgeType.LOCATES,
        weight=max(0.1, settlement_tile.fertility),
        payload={"coord": settlement_coord},
    )

    world.entities[settlement_id] = Entity(
        id=settlement_id,
        type=EntityType.SETTLEMENT,
        subtype=SettlementSubtype.AGRARIAN_VILLAGE,
        name="Settlement_01",
        coordinates=[settlement_coord],
        state=EntityState(integrity=1.0, wealth=0.66, function=1.0, active=True, status_label="Stable"),
        root_provenance_id=settlement_node.id,
    )
    world.entities[lumber_id] = Entity(
        id=lumber_id,
        type=EntityType.LUMBER_CAMP,
        subtype=None,
        name="LumberCamp_02",
        coordinates=[lumber_coord],
        state=EntityState(integrity=1.0, wealth=0.5, function=0.82, active=True, status_label="Stable"),
        root_provenance_id=lumber_node.id,
    )


def _best_settlement_coord(world: World) -> tuple[int, int]:
    candidates = [
        (tile.fertility + tile.water_flow - abs(tile.elevation) * 0.15, coord)
        for coord, tile in world.baseline.items()
        if tile.elevation > -0.05 and tile.fertility > 0.35
    ]
    if not candidates:
        raise RuntimeError("substrate produced no viable settlement candidate")
    return max(candidates)[1]


def _best_lumber_coord_near(world: World, origin: tuple[int, int]) -> tuple[int, int]:
    ox, oy = origin
    candidates = []
    for coord, tile in world.baseline.items():
        x, y = coord
        distance = abs(x - ox) + abs(y - oy)
        if distance <= max(12, world.size // 8) and tile.timber > 0.25:
            score = tile.timber - distance * 0.01
            candidates.append((score, coord))
    if not candidates:
        candidates = [(tile.timber, coord) for coord, tile in world.baseline.items() if tile.timber > 0.0]
    if not candidates:
        raise RuntimeError("substrate produced no timber candidate")
    return max(candidates)[1]
