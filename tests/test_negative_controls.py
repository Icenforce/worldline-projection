from worldline.negative_controls import (
    compare_worldline_vs_control_a,
    compare_worldline_vs_control_a_route_cut,
    compare_worldline_vs_control_b,
    compare_worldline_vs_control_b_route_cut,
    compare_worldline_vs_control_c,
    compare_worldline_vs_control_c_route_cut,
    compact_control_route_cut,
    compact_control_timber_collapse,
    explain_control_entity,
    find_control_route_conflict_triplet,
    find_control_timber_dependency_pair,
    generate_control_a,
    generate_control_b,
    generate_control_c,
    inject_control_route_cut,
    inject_control_timber_destruction,
)


def test_control_a_is_random_and_uncoupled():
    world = generate_control_a(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    explanation = explain_control_entity(world, pair.settlement_id)

    assert "random_summary" in explanation
    assert "random uncoupled placement" in explanation
    assert "posthoc_explanation" not in explanation


def test_control_b_is_spatially_plausible_without_posthoc_templates():
    world = generate_control_b(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    explanation = explain_control_entity(world, pair.settlement_id)

    assert "heuristic_summary" in explanation
    assert "heuristic siting" in explanation
    assert "posthoc_explanation" not in explanation
    assert "executable provenance edges" in explanation


def test_control_c_produces_plausible_initial_posthoc_explanation():
    world = generate_control_c(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    explanation = explain_control_entity(world, pair.settlement_id)

    assert "posthoc_explanation" in explanation
    assert "fertility=" in explanation
    assert "water_flow=" in explanation
    assert "timber" in explanation
    assert "promises construction support" in explanation


def test_worldline_beats_controls_after_timber_perturbation_and_compaction():
    for comparison in (
        compare_worldline_vs_control_a(seed=12345, size=128),
        compare_worldline_vs_control_b(seed=12345, size=128),
        compare_worldline_vs_control_c(seed=12345, size=128),
    ):
        assert comparison.worldline_compaction_retention_valid
        assert not comparison.control_compaction_retention_valid
        assert comparison.worldline_contradiction_count < comparison.control_contradiction_count


def test_control_c_updates_timber_explanation_heuristically_but_still_fails_causal_validity():
    world = generate_control_c(seed=12345, size=128)
    pair = find_control_timber_dependency_pair(world)

    inject_control_timber_destruction(world, magnitude=0.9, t=100)
    compact_control_timber_collapse(world, t=142)
    explanation = explain_control_entity(world, pair.settlement_id)

    assert "status=Poor" in explanation
    assert "timber destruction" in explanation
    assert "heuristic update" in explanation
    assert "CompactionArchiveEvent" not in explanation
    assert "typed dependency edge" in explanation
    assert "promises construction support" in explanation


def test_control_b_route_cut_is_coherent_but_non_executable():
    world = generate_control_b(seed=12345, size=128)
    triplet = find_control_route_conflict_triplet(world)

    inject_control_route_cut(world, magnitude=0.75, t=120)
    compact_control_route_cut(world, t=160)
    explanation = explain_control_entity(world, triplet.battlefield_id)

    assert "heuristic_summary" in explanation
    assert "battlefield heuristic" in explanation
    assert "RouteCut" in explanation
    assert "CompactionArchiveEvent" not in explanation
    assert "typed dependency edge" in explanation


def test_control_c_produces_plausible_route_cut_battlefield_explanation():
    world = generate_control_c(seed=12345, size=128)
    triplet = find_control_route_conflict_triplet(world)

    explanation = explain_control_entity(world, triplet.battlefield_id)

    assert "posthoc_explanation" in explanation
    assert "Battlefield inferred" in explanation
    assert "roads often imply conflict corridors" in explanation


def test_worldline_beats_controls_after_route_cut_and_compaction():
    for comparison in (
        compare_worldline_vs_control_a_route_cut(seed=12345, size=128),
        compare_worldline_vs_control_b_route_cut(seed=12345, size=128),
        compare_worldline_vs_control_c_route_cut(seed=12345, size=128),
    ):
        assert comparison.worldline_compaction_retention_valid
        assert not comparison.control_compaction_retention_valid
        assert comparison.worldline_contradiction_count < comparison.control_contradiction_count


def test_control_c_updates_route_cut_explanation_heuristically_but_lacks_executable_retention():
    world = generate_control_c(seed=12345, size=128)
    triplet = find_control_route_conflict_triplet(world)

    inject_control_route_cut(world, magnitude=0.75, t=120)
    compact_control_route_cut(world, t=160)
    explanation = explain_control_entity(world, triplet.battlefield_id)

    assert "RouteCut" in explanation
    assert "heuristic update" in explanation
    assert "narrative coherence" in explanation
    assert "CompactionArchiveEvent" not in explanation
    assert "typed dependency edge" in explanation
    assert "entity-specific causal archive survives" in explanation
