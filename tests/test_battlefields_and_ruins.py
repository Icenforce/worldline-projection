from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType, NodeType



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
        assert world.entities[route_node.entity_id].type == EntityType.ROAD



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
