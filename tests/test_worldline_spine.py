from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType, NodeType
from worldline.perturb import (
    compact_route_cut,
    compact_perturbation_consequences,
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
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    perturbation = inject_timber_destruction(world, magnitude=0.9, t=100)
    bundle = compact_perturbation_consequences(world, perturbation_ids=[perturbation.id], t=142)

    explanation = explain_entity(world, settlement_id)
    assert "timber collapse archive" in explanation
    assert "CompactionArchiveEvent" in explanation

    archive_node = world.provenance.nodes[bundle.archive_node_id]
    assert archive_node.payload["source_perturbation_ids"] == [perturbation.id]
    assert settlement_id in archive_node.payload["affected_entity_ids"]
    assert lumber_id in archive_node.payload["affected_entity_ids"]
    assert archive_node.payload["typed_provenance_links"]
    assert archive_node.payload["affected_entities"][str(settlement_id)]["state_deltas"]

    patch = world.patches[bundle.patch_id]
    assert patch.archive_event_ids == [bundle.archive_node_id]
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


def test_route_cut_compaction_preserves_conflict_explanation_and_bundle():
    world = generate_world(seed=12345, size=128)
    road_id, fort_id, battlefield_id = find_route_conflict_triplet(world)
    perturbation = inject_route_cut(world, magnitude=0.75, t=120)
    archive_id = compact_route_cut(world, t=160)

    explanation = explain_entity(world, battlefield_id)
    assert "route cut archive" in explanation
    assert "CompactionArchiveEvent" in explanation

    archive_node = world.provenance.nodes[archive_id]
    assert archive_node.payload["source_perturbation_ids"] == [perturbation.id]
    assert road_id in archive_node.payload["affected_entity_ids"]
    assert fort_id in archive_node.payload["affected_entity_ids"]
    assert battlefield_id in archive_node.payload["affected_entity_ids"]
    assert archive_node.payload["typed_provenance_links"]
    assert archive_node.payload["affected_entities"][str(battlefield_id)]["state_deltas"]

    patches = [patch for patch in world.patches.values() if patch.archive_event_ids == [archive_id]]
    assert len(patches) == 1
    assert patches[0].tile_overrides


def test_composite_compaction_preserves_distinct_timber_and_route_cut_groups():
    world = generate_world(seed=12345, size=128)
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    road_id, fort_id, battlefield_id = find_route_conflict_triplet(world)

    timber = inject_timber_destruction(world, magnitude=0.9, t=100)
    route_cut = inject_route_cut(world, magnitude=0.75, t=120)
    bundle = compact_perturbation_consequences(world, perturbation_ids=[timber.id, route_cut.id], t=180)

    archive_node = world.provenance.nodes[bundle.archive_node_id]
    payload = archive_node.payload
    assert payload["event_type"] == "CompositeConsequenceBundle"
    assert payload["source_perturbation_ids"] == [timber.id, route_cut.id]

    assert payload["affected_entity_groups"][str(timber.id)]
    assert payload["affected_entity_groups"][str(route_cut.id)]
    assert settlement_id in payload["affected_entity_groups"][str(timber.id)]
    assert lumber_id in payload["affected_entity_groups"][str(timber.id)]
    assert road_id in payload["affected_entity_groups"][str(route_cut.id)]
    assert fort_id in payload["affected_entity_groups"][str(route_cut.id)]
    assert battlefield_id in payload["affected_entity_groups"][str(route_cut.id)]

    source_groups = {group["source_perturbation_id"]: group for group in payload["source_groups"]}
    assert set(source_groups) == {timber.id, route_cut.id}
    assert source_groups[timber.id]["target_layer"] == "timber"
    assert source_groups[route_cut.id]["target_layer"] == "route"
    assert source_groups[timber.id]["affected_entities"][str(settlement_id)]["state_deltas"]
    assert source_groups[route_cut.id]["affected_entities"][str(battlefield_id)]["state_deltas"]
    assert all(link["source_perturbation_id"] == timber.id for link in source_groups[timber.id]["typed_provenance_links"])
    assert all(link["source_perturbation_id"] == route_cut.id for link in source_groups[route_cut.id]["typed_provenance_links"])

    causal_ids = {entry[2] for entry in payload["causal_sequence"]}
    assert causal_ids == {timber.id, route_cut.id}
    assert any("timber damaged" in entry[3] for entry in payload["causal_sequence"] if entry[2] == timber.id)
    assert any("route damaged" in entry[3] for entry in payload["causal_sequence"] if entry[2] == route_cut.id)

    assert len(bundle.patch_ids) == 2
    patches = [world.patches[patch_id] for patch_id in bundle.patch_ids]
    assert all(patch.archive_event_ids == [bundle.archive_node_id] for patch in patches)
    assert len({patch.region_id for patch in patches}) == 2
