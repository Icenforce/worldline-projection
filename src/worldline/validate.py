"""Validation helpers for the v0.3 prototype."""

from __future__ import annotations

from dataclasses import dataclass

from worldline.models import NodeType
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


def run_validation(world: World) -> list[ValidationResult]:
    return [
        validate_no_orphan_entities(world),
        validate_load_bearing_edges(world),
        validate_compaction_archive_present(world),
    ]
