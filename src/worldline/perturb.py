"""Perturbation and resolver skeleton for the first proof scenario."""

from __future__ import annotations

from worldline.models import EdgeType, EntityType, NodeType, Perturbation, PerturbationType
from worldline.world import World


def find_timber_dependency_pair(world: World) -> tuple[int, int]:
    """Return (settlement_id, lumber_camp_id) for the strongest current timber dependency."""

    best: tuple[float, int, int] | None = None
    for edge in world.provenance.edges.values():
        if edge.edge_type != EdgeType.SUPPLIES:
            continue
        source = world.provenance.nodes[edge.source_node_id]
        target = world.provenance.nodes[edge.target_node_id]
        if source.entity_id is None or target.entity_id is None:
            continue
        source_entity = world.entities[source.entity_id]
        target_entity = world.entities[target.entity_id]
        if source_entity.type == EntityType.LUMBER_CAMP and target_entity.type == EntityType.SETTLEMENT:
            candidate = (edge.weight, target_entity.id, source_entity.id)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None:
        raise RuntimeError("no settlement with lumber-camp dependency found")
    return best[1], best[2]


def inject_timber_destruction(world: World, *, magnitude: float = 0.9, t: int = 100) -> Perturbation:
    settlement_id, lumber_id = find_timber_dependency_pair(world)
    lumber = world.entities[lumber_id]
    settlement = world.entities[settlement_id]
    origin = lumber.coordinates[0]

    perturbation = Perturbation(
        id=len(world.perturbations) + 1,
        t=t,
        type=PerturbationType.RESOURCE_DESTRUCTION,
        origin=origin,
        radius=5,
        magnitude=magnitude,
        target_layer="timber",
        payload={"region_id": "demo_timber_region", "lumber_camp_id": lumber_id, "settlement_id": settlement_id},
    )
    world.perturbations[perturbation.id] = perturbation

    perturb_node = world.provenance.add_node(
        NodeType.PERTURBATION_EVENT,
        "timber destruction near lumber dependency",
        event_id=perturbation.id,
        payload={"magnitude": magnitude, "target_layer": "timber", "origin": origin},
    )

    old_lumber_function = lumber.state.function
    lumber.state.function = max(0.0, lumber.state.function * (1.0 - magnitude * 0.83))
    lumber.state.stale = True
    lumber.state.clamp()

    old_settlement_wealth = settlement.state.wealth
    settlement.state.wealth = max(0.0, settlement.state.wealth - magnitude * 0.28)
    settlement.state.function = max(0.0, settlement.state.function - magnitude * 0.20)
    settlement.state.stale = True
    settlement.state.clamp()

    world.provenance.add_edge(
        perturb_node.id,
        lumber.root_provenance_id,
        EdgeType.DAMAGES,
        weight=magnitude,
        payload={"old_function": old_lumber_function, "new_function": lumber.state.function},
    )
    world.provenance.add_edge(
        perturb_node.id,
        settlement.root_provenance_id,
        EdgeType.DAMAGES,
        weight=magnitude,
        payload={"old_wealth": old_settlement_wealth, "new_wealth": settlement.state.wealth},
    )
    return perturbation


def compact_timber_collapse(world: World, *, t: int = 142) -> int:
    """Create a compaction archive node without erasing causal explanation."""

    settlement_id, lumber_id = find_timber_dependency_pair(world)
    settlement = world.entities[settlement_id]
    lumber = world.entities[lumber_id]
    archive_node = world.provenance.add_node(
        NodeType.COMPACTION_ARCHIVE_EVENT,
        "timber collapse archive for generated lumber dependency",
        payload={
            "event_type": "TimberCollapse",
            "time_range": [100, t],
            "spatial_scope": "demo_timber_region",
            "source_perturbation_ids": list(world.perturbations.keys()),
            "affected_entities": {
                settlement.name: {
                    "dependency_loss": 0.90,
                    "wealth": settlement.state.wealth,
                    "function": settlement.state.function,
                },
                lumber.name: {
                    "dependency_loss": 0.90,
                    "function": lumber.state.function,
                },
            },
            "causal_sequence": [
                [100, "ResourceDestruction", "timber field damaged"],
                [115, "LumberCamp function collapse", "timber extraction degraded"],
                [142, "Settlement degradation", "wealth/function declined"],
            ],
        },
    )
    world.provenance.add_edge(
        archive_node.id,
        settlement.root_provenance_id,
        EdgeType.CAUSES,
        weight=0.9,
        payload={"compacted": True, "meaning_preserved": True},
    )
    world.provenance.add_edge(
        archive_node.id,
        lumber.root_provenance_id,
        EdgeType.CAUSES,
        weight=0.9,
        payload={"compacted": True, "meaning_preserved": True},
    )
    return archive_node.id
