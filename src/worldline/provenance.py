"""Small explicit provenance graph implementation.

The graph is deliberately simple: dictionaries of nodes and edges. The goal is to keep
causal logic visible rather than hidden behind a graph framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worldline.models import EdgeType, NodeType, ProvenanceEdge, ProvenanceNode


@dataclass
class ProvenanceGraph:
    nodes: dict[int, ProvenanceNode] = field(default_factory=dict)
    edges: dict[int, ProvenanceEdge] = field(default_factory=dict)
    _next_node_id: int = 1
    _next_edge_id: int = 1

    def add_node(
        self,
        node_type: NodeType,
        label: str,
        *,
        entity_id: int | None = None,
        event_id: int | None = None,
        payload: dict | None = None,
    ) -> ProvenanceNode:
        node = ProvenanceNode(
            id=self._next_node_id,
            node_type=node_type,
            label=label,
            entity_id=entity_id,
            event_id=event_id,
            payload=payload or {},
        )
        self.nodes[node.id] = node
        self._next_node_id += 1
        return node

    def add_edge(
        self,
        source_node_id: int,
        target_node_id: int,
        edge_type: EdgeType,
        *,
        weight: float = 1.0,
        payload: dict | None = None,
        load_bearing: bool = True,
    ) -> ProvenanceEdge:
        if source_node_id not in self.nodes:
            raise KeyError(f"source node does not exist: {source_node_id}")
        if target_node_id not in self.nodes:
            raise KeyError(f"target node does not exist: {target_node_id}")

        edge = ProvenanceEdge(
            id=self._next_edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            weight=weight,
            payload=payload or {},
            load_bearing=load_bearing,
        )
        self.edges[edge.id] = edge
        self._next_edge_id += 1
        return edge

    def parents_of(self, node_id: int) -> list[tuple[ProvenanceEdge, ProvenanceNode]]:
        parents: list[tuple[ProvenanceEdge, ProvenanceNode]] = []
        for edge in self.edges.values():
            if edge.target_node_id == node_id:
                parents.append((edge, self.nodes[edge.source_node_id]))
        return parents

    def children_of(self, node_id: int) -> list[tuple[ProvenanceEdge, ProvenanceNode]]:
        children: list[tuple[ProvenanceEdge, ProvenanceNode]] = []
        for edge in self.edges.values():
            if edge.source_node_id == node_id:
                children.append((edge, self.nodes[edge.target_node_id]))
        return children

    def load_bearing_parent_count(self, node_id: int) -> int:
        return sum(1 for edge, _ in self.parents_of(node_id) if edge.load_bearing)

    def explain_node(self, node_id: int, *, depth: int = 2) -> list[str]:
        if node_id not in self.nodes:
            raise KeyError(f"node does not exist: {node_id}")

        lines: list[str] = []

        def walk(current_id: int, level: int) -> None:
            node = self.nodes[current_id]
            prefix = "  " * level
            lines.append(f"{prefix}- {node.node_type}: {node.label}")
            if level >= depth:
                return
            for edge, parent in self.parents_of(current_id):
                marker = "load-bearing" if edge.load_bearing else "ornamental"
                lines.append(
                    f"{prefix}  <- {edge.edge_type} ({marker}, weight={edge.weight:.2f})"
                )
                walk(parent.id, level + 1)

        walk(node_id, 0)
        return lines
