from worldline.generate import generate_world
from worldline.models import EntityType
from worldline.perturb import (
    compact_timber_collapse,
    find_timber_dependency_pair,
    inject_timber_destruction,
)
from worldline.query import explain_entity
from worldline.validate import run_validation


def test_seed_generation_creates_accountable_entities():
    world = generate_world(seed=12345, size=128)
    assert world.seed == 12345
    assert world.size == 128
    assert len(world.baseline) == 128 * 128

    settlements = [entity for entity in world.entities.values() if entity.type == EntityType.SETTLEMENT]
    lumber_camps = [entity for entity in world.entities.values() if entity.type == EntityType.LUMBER_CAMP]
    assert settlements
    assert lumber_camps


def test_perturbation_degrades_generated_timber_dependent_settlement():
    world = generate_world(seed=12345, size=128)
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    before_wealth = world.entities[settlement_id].state.wealth
    before_lumber_function = world.entities[lumber_id].state.function

    inject_timber_destruction(world, magnitude=0.9, t=100)

    assert world.entities[settlement_id].state.wealth < before_wealth
    assert world.entities[lumber_id].state.function < before_lumber_function
    assert "timber destruction" in explain_entity(world, settlement_id)


def test_compaction_preserves_generated_dependency_explanation():
    world = generate_world(seed=12345, size=128)
    settlement_id, _ = find_timber_dependency_pair(world)
    inject_timber_destruction(world, magnitude=0.9, t=100)
    compact_timber_collapse(world, t=142)

    explanation = explain_entity(world, settlement_id)
    assert "timber collapse archive" in explanation
    assert "CompactionArchiveEvent" in explanation

    results = run_validation(world)
    assert all(result.passed for result in results)
