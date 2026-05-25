from worldline.negative_controls import (
    compare_worldline_vs_control_c,
    compact_control_timber_collapse,
    explain_control_entity,
    find_control_timber_dependency_pair,
    generate_control_c,
    inject_control_timber_destruction,
)


def test_control_c_produces_plausible_initial_posthoc_explanation():
    world = generate_control_c(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    explanation = explain_control_entity(world, pair.settlement_id)

    assert "posthoc_explanation" in explanation
    assert "fertility=" in explanation
    assert "water_flow=" in explanation
    assert "timber" in explanation
    assert "promises construction support" in explanation


def test_worldline_beats_control_c_after_perturbation_and_compaction():
    comparison = compare_worldline_vs_control_c(seed=12345, size=128)

    assert comparison.worldline_post_perturbation_valid
    assert not comparison.control_post_perturbation_valid
    assert comparison.worldline_compaction_retention_valid
    assert not comparison.control_compaction_retention_valid
    assert comparison.worldline_contradiction_count < comparison.control_contradiction_count


def test_control_c_explanation_stays_stale_after_timber_perturbation_and_compaction():
    world = generate_control_c(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    inject_control_timber_destruction(world, magnitude=0.9, t=100)
    compact_control_timber_collapse(world, t=142)
    explanation = explain_control_entity(world, pair.settlement_id)

    assert "status=Poor" in explanation
    assert "timber destruction" not in explanation
    assert "CompactionArchiveEvent" not in explanation
    assert "promises construction support" in explanation
