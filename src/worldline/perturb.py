"""Perturbation and resolver skeleton for the first proof scenario."""

from __future__ import annotations

from worldline.models import EdgeType, NodeType, Perturbation, PerturbationType
from worldline.world import World


def inject_timber_destruction(world: World, *, magnitude: float = 0.9, t: int = 100) -> Perturbation:
    perturbation = Perturbation(
        id=len(world.perturbations) + 1,
        t=t,
        type=PerturbationType.RESOURCE_DESTRUCTION,
        origin=(48, 72),
        radius=5,
        magnitude=magnitude,
        target_layer="timber",
        payload={"region_id": "Chunk_3_5"},
    )
    world.perturbations[perturbation.id] = perturbation

    perturb_node = world.provenance.add_node(
        NodeType.PERTURBATION_EVENT,
        "timber destruction in North Basin",
        event_id=perturbation.id,
        payload={"magnitude": magnitude, "target_layer": "timber"},
    )

    # Demo-specific propagation: damage LumberCamp_02, then Settlement_01.
    lumber = world.entities[2]
    settlement = world.entities[1]

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

    settlement = world.entities[1]
    lumber = world.entities[2]
    archive_node = world.provenance.add_node(
        NodeType.COMPACTION_ARCHIVE_EVENT,
        "North Basin timber collapse archive",
        payload={
            "event_type": "TimberCollapse",
            "time_range": [100, t],
            "spatial_scope": "Chunk_3_5",
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
