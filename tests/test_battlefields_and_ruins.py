from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType, NodeType
from worldline.query import explain_entity
from worldline.validate import validate_accountable_entity_placement



def test_battlefield_is_route_derived():
    world = generate_world(seed=12345, size=128)
    battlefields = [entity for entity in world.entities.values() if entity.type == EntityType.BATTLEFIELD]

    assert battlefields
    for battlefield in battlefields:
        parent_edges = [
            edge for edge in world.provenance.edges.values() if edge.target_node_id == battlefield.root_provenance_id
        ]
        assert any(edge.edge_type == EdgeType.ENABLES for edge in parent_edges)
        assert any(edge.edge_type == EdgeType.CAUSES for edge in parent_edges)

        route_edge = next(edge for edge in parent_edges if edge.edge_type == EdgeType.ENABLES)
        route_node = world.provenance.nodes[route_edge.source_node_id]
        assert route_node.entity_id is not None
        road = world.entities[route_node.entity_id]
        assert road.type == EntityType.ROAD

        conflict_node = world.provenance.nodes[
            next(edge.source_node_id for edge in parent_edges if edge.edge_type == EdgeType.CAUSES)
        ]
        fort = world.entities[conflict_node.payload["fort_entity"]]

        assert battlefield.coordinates[0] in road.coordinates
        assert 0 < road.coordinates.index(battlefield.coordinates[0]) < len(road.coordinates) - 1
        assert fort.coordinates[0] in road.coordinates
        assert battlefield.coordinates[0] != fort.coordinates[0]



def test_ruin_has_terrain_and_abandonment_provenance():
    world = generate_world(seed=12345, size=128)
    ruins = [entity for entity in world.entities.values() if entity.type == EntityType.RUIN]

    assert ruins
    for ruin in ruins:
        parent_edges = [edge for edge in world.provenance.edges.values() if edge.target_node_id == ruin.root_provenance_id]
        locate_edge = next(edge for edge in parent_edges if edge.edge_type == EdgeType.LOCATES)
        cause_edge = next(edge for edge in parent_edges if edge.edge_type == EdgeType.CAUSES)

        locate_parent = world.provenance.nodes[locate_edge.source_node_id]
        cause_parent = world.provenance.nodes[cause_edge.source_node_id]
        assert locate_parent.node_type == NodeType.SUBSTRATE_PRECONDITION
        assert cause_parent.node_type == NodeType.HISTORICAL_EVENT



def test_battlefield_and_ruin_pass_accountable_placement_validation():
    world = generate_world(seed=12345, size=128)

    result = validate_accountable_entity_placement(world)

    assert result.passed



def test_ruin_query_explanation_mentions_terrain_and_abandonment():
    world = generate_world(seed=12345, size=128)
    ruin = next(entity for entity in world.entities.values() if entity.type == EntityType.RUIN)

    explanation = explain_entity(world, ruin.id)

    assert "marginal terrain" in explanation
    assert "abandonment of precursor settlement" in explanation



def test_validation_catches_missing_battlefield_then_ruin_cause_edges():
    battlefield_world = generate_world(seed=12345, size=128)
    battlefield = next(entity for entity in battlefield_world.entities.values() if entity.type == EntityType.BATTLEFIELD)
    battlefield_cause_edge_id = next(
        edge.id
        for edge in battlefield_world.provenance.edges.values()
        if edge.target_node_id == battlefield.root_provenance_id and edge.edge_type == EdgeType.CAUSES
    )
    del battlefield_world.provenance.edges[battlefield_cause_edge_id]

    battlefield_result = validate_accountable_entity_placement(battlefield_world)
    assert not battlefield_result.passed
    assert battlefield.name in battlefield_result.details

    ruin_world = generate_world(seed=12345, size=128)
    ruin = next(entity for entity in ruin_world.entities.values() if entity.type == EntityType.RUIN)
    ruin_cause_edge_id = next(
        edge.id
        for edge in ruin_world.provenance.edges.values()
        if edge.target_node_id == ruin.root_provenance_id and edge.edge_type == EdgeType.CAUSES
    )
    del ruin_world.provenance.edges[ruin_cause_edge_id]

    ruin_result = validate_accountable_entity_placement(ruin_world)
    assert not ruin_result.passed
    assert ruin.name in ruin_result.details
