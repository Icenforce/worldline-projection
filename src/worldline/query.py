"""Query helpers for structural explanations."""

from __future__ import annotations

from worldline.world import World


def explain_entity(world: World, entity_id: int, *, depth: int = 3) -> str:
    entity = world.entities[entity_id]
    lines = [
        f"{entity.name} [{entity.type}]",
        f"status={entity.state.status_label} wealth={entity.state.wealth:.2f} function={entity.state.function:.2f}",
        "provenance:",
    ]
    lines.extend(world.provenance.explain_node(entity.root_provenance_id, depth=depth))
    return "\n".join(lines)
