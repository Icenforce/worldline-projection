from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType, NodeType
from worldline.perturb import (
    compact_timber_collapse,
    find_timber_dependency_pair,
    find_route_conflict_triplet,
    inject_route_cut,
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
    assert world.entities[settlement_id].state.status_label == "Poor"
    assert world.entities[lumber_id].state.function < before_lumber_function
    assert "timber destruction" in explain_entity(world, settlement_id)


def test_perturbation_propagates_along_existing_provenance_edges():
    world = generate_world(seed=12345, size=128)
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    settlement = world.entities[settlement_id]
    lumber = world.entities[lumber_id]

    inject_timber_destruction(world, magnitude=0.9, t=100)

    direct_damage_edges = [
        edge
        for edge in world.provenance.edges.values()
        if edge.edge_type == EdgeType.DAMAGES
        and edge.source_node_id in world.provenance.nodes
        and world.provenance.nodes[edge.source_node_id].node_type == NodeType.PERTURBATION_EVENT
        and edge.target_node_id == settlement.root_provenance_id
    ]
    propagated_damage_edges = [
        edge
        for edge in world.provenance.edges.values()
        if edge.edge_type == EdgeType.DAMAGES
        and edge.source_node_id == lumber.root_provenance_id
        and edge.target_node_id == settlement.root_provenance_id
        and edge.payload.get("propagated_via") == EdgeType.SUPPLIES
    ]

    assert not direct_damage_edges
    assert propagated_damage_edges
    assert all(edge.load_bearing and edge.weight > 0.0 for edge in propagated_damage_edges)


def test_compaction_preserves_generated_dependency_explanation():
    world = generate_world(seed=12345, size=128)
    settlement_id, _ = find_timber_dependency_pair(world)
    inject_timber_destruction(world, magnitude=0.9, t=100)
    archive_id = compact_timber_collapse(world, t=142)

    explanation = explain_entity(world, settlement_id)
    assert "timber collapse archive" in explanation
    assert "CompactionArchiveEvent" in explanation

    assert world.patches
    patch = next(iter(world.patches.values()))
    assert patch.archive_event_ids == [archive_id]
    assert patch.tile_overrides

    results = run_validation(world)
    assert all(result.passed for result in results)


def test_route_cut_degrades_conflict_corridor_and_explains_impact():
    world = generate_world(seed=12345, size=128)
    road_id, fort_id, battlefield_id = find_route_conflict_triplet(world)
    road = world.entities[road_id]
    fort = world.entities[fort_id]
    battlefield = world.entities[battlefield_id]
    before_road_function = road.state.function
    before_fort_function = fort.state.function
    before_battlefield_function = battlefield.state.function

    inject_route_cut(world, magnitude=0.75, t=120)

    assert road.state.function < before_road_function
    assert fort.state.function < before_fort_function
    assert battlefield.state.function < before_battlefield_function

    road_damage_edges = [
        edge
        for edge in world.provenance.edges.values()
        if edge.edge_type == EdgeType.DAMAGES
        and edge.target_node_id == road.root_provenance_id
        and world.provenance.nodes[edge.source_node_id].node_type == NodeType.PERTURBATION_EVENT
    ]
    assert road_damage_edges

    explanation = explain_entity(world, battlefield_id)
    assert "route cut" in explanation
    assert road.name in explanation
