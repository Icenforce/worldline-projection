from worldline.generate import generate_world
from worldline.perturb import compact_timber_collapse, inject_timber_destruction
from worldline.query import explain_entity
from worldline.validate import run_validation


def test_seed_generation_creates_demo_entities():
    world = generate_world(seed=12345, size=128)
    assert world.seed == 12345
    assert world.size == 128
    assert len(world.baseline) == 128 * 128
    assert world.entities[1].name == "Settlement_01"
    assert world.entities[2].name == "LumberCamp_02"


def test_perturbation_degrades_timber_dependent_settlement():
    world = generate_world(seed=12345, size=128)
    before_wealth = world.entities[1].state.wealth
    before_lumber_function = world.entities[2].state.function

    inject_timber_destruction(world, magnitude=0.9, t=100)

    assert world.entities[1].state.wealth < before_wealth
    assert world.entities[2].state.function < before_lumber_function
    assert "timber destruction" in explain_entity(world, 1)


def test_compaction_preserves_explanation():
    world = generate_world(seed=12345, size=128)
    inject_timber_destruction(world, magnitude=0.9, t=100)
    compact_timber_collapse(world, t=142)

    explanation = explain_entity(world, 1)
    assert "North Basin timber collapse archive" in explanation
    assert "CompactionArchiveEvent" in explanation

    results = run_validation(world)
    assert all(result.passed for result in results)
