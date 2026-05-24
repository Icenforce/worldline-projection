"""Validation helpers for the v0.3 prototype."""

from __future__ import annotations

from dataclasses import dataclass

from worldline.models import EdgeType, Entity, EntityType, NodeType
from worldline.world import World


@dataclass
class ValidationResult:
    name: str
    passed: bool
    details: str


def validate_no_orphan_entities(world: World) -> ValidationResult:
    missing = [entity.id for entity in world.entities.values() if entity.root_provenance_id not in world.provenance.nodes]
    return ValidationResult(
        name="no_orphan_entities",
        passed=not missing,
        details="all entities have root provenance" if not missing else f"missing provenance: {missing}",
    )


def validate_load_bearing_edges(world: World) -> ValidationResult:
    ornamental = [edge.id for edge in world.provenance.edges.values() if not edge.load_bearing]
    return ValidationResult(
        name="load_bearing_edges",
        passed=not ornamental,
        details="all current edges are marked load-bearing" if not ornamental else f"ornamental edges: {ornamental}",
    )


def validate_accountable_entity_placement(world: World) -> ValidationResult:
    invalid: list[str] = []
    for entity in world.entities.values():
        if not _entity_has_valid_placement(world, entity):
            invalid.append(entity.name)
    return ValidationResult(
        name="accountable_entity_placement",
        passed=not invalid,
        details=(
            "all entity placements satisfy subtype-specific provenance"
            if not invalid
            else f"invalid subtype placement: {invalid}"
        ),
    )


def validate_compaction_archive_present(world: World) -> ValidationResult:
    archives = [
        node.id
        for node in world.provenance.nodes.values()
        if node.node_type == NodeType.COMPACTION_ARCHIVE_EVENT
    ]
    return ValidationResult(
        name="compaction_archive_present",
        passed=bool(archives),
        details=f"archive nodes: {archives}" if archives else "no compaction archive nodes present",
    )


def validate_compaction_patches_present(world: World) -> ValidationResult:
    patches = list(world.patches.values())
    linked_patches = [patch.id for patch in patches if patch.archive_event_ids and patch.tile_overrides]
    return ValidationResult(
        name="compaction_patches_present",
        passed=bool(linked_patches),
        details=(
            f"linked patches: {linked_patches}" if linked_patches else "no linked LocalBaselinePatch records present"
        ),
    )


def _entity_has_valid_placement(world: World, entity: Entity) -> bool:
    parents = world.provenance.parents_of(entity.root_provenance_id)
    if not parents:
        return False

    if entity.type == EntityType.SETTLEMENT:
        return _has_parent(world, parents, EdgeType.LOCATES, NodeType.SUBSTRATE_PRECONDITION) and _has_parent(
            world, parents, EdgeType.REQUIRES, NodeType.SUBSTRATE_PRECONDITION
        )

    if entity.type in {EntityType.LUMBER_CAMP, EntityType.MINE}:
        return _has_parent(world, parents, EdgeType.ENABLES, NodeType.SUBSTRATE_PRECONDITION)

    if entity.type == EntityType.ROAD:
        return _has_parent(world, parents, EdgeType.LOCATES, NodeType.SUBSTRATE_PRECONDITION)

    if entity.type == EntityType.FORT:
        road_parent = _has_parent(
            world, parents, EdgeType.ENABLES, NodeType.GENERATED_ENTITY, entity_type=EntityType.ROAD
        )
        locate_parent = _has_parent(world, parents, EdgeType.LOCATES, NodeType.SUBSTRATE_PRECONDITION)
        require_parent = _has_parent(world, parents, EdgeType.REQUIRES, NodeType.SUBSTRATE_PRECONDITION)
        return road_parent and locate_parent and require_parent

    if entity.type == EntityType.BATTLEFIELD:
        road_parent = _has_parent(
            world, parents, EdgeType.ENABLES, NodeType.GENERATED_ENTITY, entity_type=EntityType.ROAD
        )
        locate_parent = _has_parent(world, parents, EdgeType.LOCATES, NodeType.SUBSTRATE_PRECONDITION)
        cause_parent = _has_parent(world, parents, EdgeType.CAUSES, NodeType.HISTORICAL_EVENT)
        return road_parent and locate_parent and cause_parent

    if entity.type == EntityType.RUIN:
        return _has_parent(world, parents, EdgeType.LOCATES, NodeType.SUBSTRATE_PRECONDITION) and _has_parent(
            world, parents, EdgeType.CAUSES, NodeType.HISTORICAL_EVENT
        )

    return True



def _has_parent(
    world: World,
    parents: list[tuple],
    edge_type: EdgeType,
    node_type: NodeType,
    *,
    entity_type: EntityType | None = None,
) -> bool:
    for edge, node in parents:
        if edge.edge_type != edge_type or node.node_type != node_type:
            continue
        if entity_type is None:
            return True
        if node.entity_id is None:
            continue
        parent_entity = world.entities.get(node.entity_id)
        if parent_entity is not None and parent_entity.type == entity_type:
            return True
    return False


def run_validation(world: World) -> list[ValidationResult]:
    return [
        validate_no_orphan_entities(world),
        validate_load_bearing_edges(world),
        validate_accountable_entity_placement(world),
        validate_compaction_archive_present(world),
        validate_compaction_patches_present(world),
    ]
