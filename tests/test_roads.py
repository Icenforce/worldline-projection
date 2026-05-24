from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType


def test_roads_are_generated_for_resource_dependencies():
    world = generate_world(seed=12345, size=128)
    roads = [entity for entity in world.entities.values() if entity.type == EntityType.ROAD]

    assert roads
    for road in roads:
        assert road.root_provenance_id in world.provenance.nodes
        assert len(road.coordinates) >= 2
        assert world.provenance.load_bearing_parent_count(road.root_provenance_id) >= 1


def test_roads_emit_transit_edges():
    world = generate_world(seed=12345, size=128)
    roads = [entity for entity in world.entities.values() if entity.type == EntityType.ROAD]
    road_node_ids = {road.root_provenance_id for road in roads}

    transit_edges = [
        edge
        for edge in world.provenance.edges.values()
        if edge.edge_type == EdgeType.TRANSITS and edge.source_node_id in road_node_ids
    ]

    assert transit_edges
    assert all(edge.load_bearing for edge in transit_edges)
    assert all(edge.weight > 0.0 for edge in transit_edges)


def test_road_transit_edges_connect_to_structural_entities():
    world = generate_world(seed=12345, size=128)
    road_node_ids = {
        entity.root_provenance_id
        for entity in world.entities.values()
        if entity.type == EntityType.ROAD
    }
    structural_target_types = {EntityType.SETTLEMENT, EntityType.LUMBER_CAMP, EntityType.MINE}

    target_entity_ids = []
    for edge in world.provenance.edges.values():
        if edge.edge_type != EdgeType.TRANSITS or edge.source_node_id not in road_node_ids:
            continue
        target_node = world.provenance.nodes[edge.target_node_id]
        if target_node.entity_id is not None:
            target_entity_ids.append(target_node.entity_id)

    assert target_entity_ids
    assert all(world.entities[entity_id].type in structural_target_types for entity_id in target_entity_ids)
