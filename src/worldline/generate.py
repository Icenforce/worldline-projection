"""Deterministic world generator for Worldline Projection."""

from __future__ import annotations

from worldline.placement import place_core_entities
from worldline.substrate import generate_substrate
from worldline.world import World


def generate_world(seed: int = 12345, size: int = 128) -> World:
    world = World(seed=seed, size=size)
    world.baseline = generate_substrate(seed=seed, size=size)
    place_core_entities(world, settlement_count=5)
    return world
