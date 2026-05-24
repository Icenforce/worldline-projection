from worldline.generate import generate_world
from worldline.substrate import generate_substrate


def test_substrate_is_reproducible_for_same_seed():
    first = generate_substrate(seed=12345, size=64)
    second = generate_substrate(seed=12345, size=64)
    assert first == second


def test_substrate_changes_with_seed():
    first = generate_substrate(seed=12345, size=64)
    second = generate_substrate(seed=54321, size=64)
    assert first != second


def test_substrate_has_expected_size_and_ranges():
    substrate = generate_substrate(seed=12345, size=64)
    assert len(substrate) == 64 * 64

    for tile in substrate.values():
        assert -1.0 <= tile.elevation <= 1.0
        assert 0.0 <= tile.slope <= 1.0
        assert 0.0 <= tile.water_flow <= 1.0
        assert tile.basin_id >= 1
        assert 0.0 <= tile.fertility <= 1.0
        assert 0.0 <= tile.timber <= 1.0
        assert 0.0 <= tile.iron <= 1.0
        assert 0.0 <= tile.coal <= 1.0


def test_generated_world_uses_substrate_fields_for_demo_entities():
    world = generate_world(seed=12345, size=64)
    settlement = world.entities[1]
    lumber = world.entities[2]

    settlement_tile = world.baseline[settlement.coordinates[0]]
    lumber_tile = world.baseline[lumber.coordinates[0]]

    assert settlement_tile.fertility > 0.35
    assert settlement_tile.elevation > -0.05
    assert lumber_tile.timber > 0.25
