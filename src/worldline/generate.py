"""Deterministic skeleton generator for Worldline Projection.

This is not the final generator. It exists to make the first timber-collapse proof
scenario concrete enough to test.
"""

from __future__ import annotations

import random

from worldline.models import (
    BaselineTile,
    EdgeType,
    Entity,
    EntityState,
    EntityType,
    NodeType,
    SettlementSubtype,
)
from worldline.world import World


def generate_world(seed: int = 12345, size: int = 128) -> World:
    rng = random.Random(seed)
    world = World(seed=seed, size=size)

    for x in range(size):
        for y in range(size):
            # Deterministic toy substrate. Replace with real layered substrate later.
            elevation = rng.uniform(-0.2, 1.0)
            water_flow = max(0.0, 1.0 - abs(y - size // 2) / (size / 2))
            fertility = min(1.0, max(0.0, water_flow * 0.8 + rng.uniform(0.0, 0.2)))
            timber = 0.9 if (size // 3 < x < size // 2 and size // 2 < y < size // 2 + 20) else rng.uniform(0.0, 0.3)
            iron = 0.8 if (x > int(size * 0.7) and y < int(size * 0.35)) else rng.uniform(0.0, 0.2)
            coal = 0.7 if (x > int(size * 0.6) and y > int(size * 0.65)) else rng.uniform(0.0, 0.2)
            world.baseline[(x, y)] = BaselineTile(
                x=x,
                y=y,
                elevation=elevation,
                slope=0.0,
                water_flow=water_flow,
                basin_id=1 if y < size // 2 else 2,
                biome="Forest" if timber > 0.5 else "Lowland",
                fertility=fertility,
                timber=timber,
                iron=iron,
                coal=coal,
            )

    _add_timber_demo_entities(world)
    return world


def _add_timber_demo_entities(world: World) -> None:
    """Create a deliberately small causal chain for the first proof scenario."""

    settlement_id = 1
    lumber_id = 2

    timber_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        "high-timber forest field in North Basin",
        payload={"field": "timber", "region_id": "Chunk_3_5", "mean_value": 0.9},
    )
    water_node = world.provenance.add_node(
        NodeType.SUBSTRATE_PRECONDITION,
        "river-adjacent fertile lowland",
        payload={"field": "water_flow/fertility"},
    )
    lumber_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        "LumberCamp_02 exploits North Basin timber",
        entity_id=lumber_id,
    )
    settlement_node = world.provenance.add_node(
        NodeType.GENERATED_ENTITY,
        "Settlement_01 depends on timber supply and river fertility",
        entity_id=settlement_id,
    )

    world.provenance.add_edge(timber_node.id, lumber_node.id, EdgeType.ENABLES, weight=0.9)
    world.provenance.add_edge(lumber_node.id, settlement_node.id, EdgeType.SUPPLIES, weight=0.9)
    world.provenance.add_edge(water_node.id, settlement_node.id, EdgeType.LOCATES, weight=0.7)

    world.entities[settlement_id] = Entity(
        id=settlement_id,
        type=EntityType.SETTLEMENT,
        subtype=SettlementSubtype.AGRARIAN_VILLAGE,
        name="Settlement_01",
        coordinates=[(50, 70)],
        state=EntityState(integrity=1.0, wealth=0.66, function=1.0, active=True, status_label="Stable"),
        root_provenance_id=settlement_node.id,
    )
    world.entities[lumber_id] = Entity(
        id=lumber_id,
        type=EntityType.LUMBER_CAMP,
        subtype=None,
        name="LumberCamp_02",
        coordinates=[(48, 72)],
        state=EntityState(integrity=1.0, wealth=0.5, function=0.82, active=True, status_label="Stable"),
        root_provenance_id=lumber_node.id,
    )
