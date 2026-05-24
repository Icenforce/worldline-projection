from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType, NodeType


def test_fort_is_generated_with_root_provenance():
    world = generate_world(seed=12345, size=128)
    forts = [entity for entity in world.entities.values() if entity.type == EntityType.FORT]

    assert forts
    for fort in forts:
        assert fort.root_provenance_id in world.provenance.nodes
        assert world.provenance.load_bearing_parent_count(fort.root_provenance_id) >= 3


def test_fort_is_connected_to_road_through_load_bearing_provenance():
    world = generate_world(seed=12345, size=128)
    roads_by_node = {
        entity.root_provenance_id: entity
        for entity in world.entities.values()
        if entity.type == EntityType.ROAD
    }
    forts = [entity for entity in world.entities.values() if entity.type == EntityType.FORT]

    assert forts
    for fort in forts:
        route_edges = [
            edge
            for edge in world.provenance.edges.values()
            if edge.target_node_id == fort.root_provenance_id
            and edge.source_node_id in roads_by_node
            and edge.edge_type == EdgeType.ENABLES
        ]
        assert route_edges
        assert all(edge.load_bearing and edge.weight > 0.0 for edge in route_edges)


def test_fort_location_is_route_derived_not_random():
    world = generate_world(seed=12345, size=128)
    forts = [entity for entity in world.entities.values() if entity.type == EntityType.FORT]

    assert forts
    for fort in forts:
        parent_edges = [
            edge for edge in world.provenance.edges.values() if edge.target_node_id == fort.root_provenance_id
        ]
        locate_edges = [edge for edge in parent_edges if edge.edge_type == EdgeType.LOCATES]
        require_edges = [edge for edge in parent_edges if edge.edge_type == EdgeType.REQUIRES]

        assert locate_edges
        assert require_edges

        locate_parent = world.provenance.nodes[locate_edges[0].source_node_id]
        require_parent = world.provenance.nodes[require_edges[0].source_node_id]
        fort_node = world.provenance.nodes[fort.root_provenance_id]
        road_entity = world.entities[fort_node.payload["road_entity"]]

        assert locate_parent.node_type == NodeType.SUBSTRATE_PRECONDITION
        assert require_parent.node_type == NodeType.SUBSTRATE_PRECONDITION
        assert fort.coordinates[0] in road_entity.coordinates
        assert 0 < road_entity.coordinates.index(fort.coordinates[0]) < len(road_entity.coordinates) - 1
        assert locate_parent.payload["coord"] == fort.coordinates[0]
        assert require_parent.payload["road_entity"] == road_entity.id
        assert require_parent.payload["path_length"] == len(road_entity.coordinates)
        assert require_parent.payload["strategic_score"] >= 0.5
