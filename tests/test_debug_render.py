from copy import deepcopy

from worldline.debug_render import render_debug_overlays, select_causal_chain
from worldline.generate import generate_world
from worldline.models import EntityType, NodeType
from worldline.perturb import find_timber_dependency_pair, inject_timber_destruction


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_render_debug_overlays_emits_expected_pngs_without_mutating_world(tmp_path):
    world = generate_world(seed=12345, size=64)
    settlement_id, _ = find_timber_dependency_pair(world)
    inject_timber_destruction(world, magnitude=0.9, t=100)

    baseline_before = deepcopy(world.baseline)
    entities_before = deepcopy(world.entities)
    provenance_edge_count = len(world.provenance.edges)
    provenance_node_count = len(world.provenance.nodes)

    overlays = render_debug_overlays(
        world,
        tmp_path,
        cell_size=2,
        chain_entity_id=settlement_id,
    )

    for path in [
        overlays.substrate,
        overlays.resources,
        overlays.entities,
        overlays.causal_chain,
    ]:
        data = path.read_bytes()
        assert data.startswith(PNG_SIGNATURE)
        assert len(data) > len(PNG_SIGNATURE)

    assert world.baseline == baseline_before
    assert world.entities == entities_before
    assert len(world.provenance.edges) == provenance_edge_count
    assert len(world.provenance.nodes) == provenance_node_count


def test_select_causal_chain_prefers_perturbation_path_when_available():
    world = generate_world(seed=12345, size=64)
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    inject_timber_destruction(world, magnitude=0.9, t=100)

    chain = select_causal_chain(world, target_entity_id=settlement_id)

    assert chain[0] in world.provenance.nodes
    assert chain[-1] == world.entities[settlement_id].root_provenance_id
    assert any(
        world.provenance.nodes[node_id].node_type == NodeType.PERTURBATION_EVENT
        for node_id in chain
    )
    assert any(
        world.provenance.nodes[node_id].entity_id == lumber_id
        and world.entities[lumber_id].type == EntityType.LUMBER_CAMP
        for node_id in chain
    )
