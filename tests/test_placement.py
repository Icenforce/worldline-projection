from worldline.generate import generate_world
from worldline.models import EdgeType, EntityType
from worldline.perturb import find_timber_dependency_pair


def test_generated_world_places_multiple_accountable_settlements():
    world = generate_world(seed=12345, size=128)
    settlements = [entity for entity in world.entities.values() if entity.type == EntityType.SETTLEMENT]

    assert len(settlements) >= 5
    for settlement in settlements:
        assert settlement.root_provenance_id in world.provenance.nodes
        assert world.provenance.load_bearing_parent_count(settlement.root_provenance_id) >= 2


def test_generated_world_places_resource_exploitation_entities():
    world = generate_world(seed=12345, size=128)
    lumber_camps = [entity for entity in world.entities.values() if entity.type == EntityType.LUMBER_CAMP]
    mines = [entity for entity in world.entities.values() if entity.type == EntityType.MINE]

    assert lumber_camps
    assert mines
    for entity in lumber_camps + mines:
        assert entity.root_provenance_id in world.provenance.nodes
        assert world.provenance.load_bearing_parent_count(entity.root_provenance_id) >= 1


def test_lumber_supply_dependency_is_explicit():
    world = generate_world(seed=12345, size=128)
    settlement_id, lumber_id = find_timber_dependency_pair(world)

    settlement = world.entities[settlement_id]
    lumber = world.entities[lumber_id]
    assert settlement.type == EntityType.SETTLEMENT
    assert lumber.type == EntityType.LUMBER_CAMP

    supply_edges = [
        edge
        for edge in world.provenance.edges.values()
        if edge.edge_type == EdgeType.SUPPLIES
        and edge.source_node_id == lumber.root_provenance_id
        and edge.target_node_id == settlement.root_provenance_id
    ]
    assert supply_edges
    assert all(edge.load_bearing for edge in supply_edges)
