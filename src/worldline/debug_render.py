"""Read-only debug overlay renderer for Worldline Projection.

This module emits PNG overlays for inspection and audit. It does not mutate world
state and does not introduce a gameplay rendering layer.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from worldline.models import EntityType, NodeType
from worldline.world import World

Coord = tuple[int, int]
Color = tuple[int, int, int, int]


@dataclass(frozen=True)
class DebugOverlaySet:
    substrate: Path
    resources: Path
    entities: Path
    causal_chain: Path
    selected_chain_node_ids: tuple[int, ...]


def render_debug_overlays(
    world: World,
    output_dir: str | Path,
    *,
    cell_size: int = 4,
    chain_entity_id: int | None = None,
    chain_source_node_id: int | None = None,
) -> DebugOverlaySet:
    """Render read-only PNG overlays for audit/debug use.

    The returned files are layered for inspection:
    - substrate.png: opaque substrate base
    - resources.png: transparent resource intensity overlay
    - entities.png: transparent entity footprint overlay
    - causal_chain.png: transparent overlay for one selected provenance chain
    """

    if cell_size < 1:
        raise ValueError("cell_size must be at least 1")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    selected_chain = select_causal_chain(
        world,
        target_entity_id=chain_entity_id,
        source_node_id=chain_source_node_id,
    )

    substrate_path = output / "substrate.png"
    resources_path = output / "resources.png"
    entities_path = output / "entities.png"
    causal_chain_path = output / "causal_chain.png"

    _write_png(substrate_path, _render_substrate(world, cell_size=cell_size))
    _write_png(resources_path, _render_resources(world, cell_size=cell_size))
    _write_png(entities_path, _render_entities(world, cell_size=cell_size))
    _write_png(
        causal_chain_path,
        _render_causal_chain(world, selected_chain, cell_size=cell_size),
    )

    return DebugOverlaySet(
        substrate=substrate_path,
        resources=resources_path,
        entities=entities_path,
        causal_chain=causal_chain_path,
        selected_chain_node_ids=tuple(selected_chain),
    )


def select_causal_chain(
    world: World,
    *,
    target_entity_id: int | None = None,
    source_node_id: int | None = None,
) -> list[int]:
    """Select one ancestry chain ending at a target entity provenance node.

    Selection policy:
    1. explicit source node to explicit/implicit target
    2. nearest perturbation-event ancestry if present
    3. strongest load-bearing parent walk to a root ancestor
    """

    target_entity = _select_target_entity(world, target_entity_id)
    target_node_id = target_entity.root_provenance_id

    if source_node_id is not None:
        chain = _find_ancestry_chain(world, start_node_id=source_node_id, target_node_id=target_node_id)
        if not chain:
            raise ValueError(f"no provenance chain from node {source_node_id} to entity {target_entity_id}")
        return chain

    perturbation_chains: list[list[int]] = []
    for node in world.provenance.nodes.values():
        if node.node_type != NodeType.PERTURBATION_EVENT:
            continue
        chain = _find_ancestry_chain(world, start_node_id=node.id, target_node_id=target_node_id)
        if chain:
            perturbation_chains.append(chain)
    if perturbation_chains:
        perturbation_chains.sort(key=lambda chain: (len(chain), -_chain_weight(world, chain)))
        return perturbation_chains[0]

    return _strongest_parent_chain(world, target_node_id)


def _select_target_entity(world: World, target_entity_id: int | None):
    if target_entity_id is not None:
        return world.entities[target_entity_id]

    if world.perturbations:
        damaged_targets = [
            world.provenance.nodes[edge.target_node_id].entity_id
            for edge in world.provenance.edges.values()
            if edge.target_node_id in world.provenance.nodes
            and edge.source_node_id in world.provenance.nodes
            and world.provenance.nodes[edge.source_node_id].node_type == NodeType.PERTURBATION_EVENT
            and world.provenance.nodes[edge.target_node_id].entity_id is not None
        ]
        if damaged_targets:
            return world.entities[damaged_targets[0]]

    if not world.entities:
        raise ValueError("world has no entities to render")
    return min(world.entities.values(), key=lambda entity: entity.id)


def _find_ancestry_chain(world: World, *, start_node_id: int, target_node_id: int) -> list[int]:
    queue: list[tuple[int, list[int]]] = [(start_node_id, [start_node_id])]
    visited: set[int] = set()
    while queue:
        current, path = queue.pop(0)
        if current == target_node_id:
            return path
        if current in visited:
            continue
        visited.add(current)
        for edge, child in sorted(
            world.provenance.children_of(current),
            key=lambda item: (-item[0].weight, item[1].id),
        ):
            if child.id in visited:
                continue
            queue.append((child.id, path + [child.id]))
    return []


def _strongest_parent_chain(world: World, target_node_id: int) -> list[int]:
    reversed_chain = [target_node_id]
    current = target_node_id
    while True:
        parents = world.provenance.parents_of(current)
        if not parents:
            break
        edge, parent = max(
            parents,
            key=lambda item: (
                1 if item[0].load_bearing else 0,
                item[0].weight,
                -item[1].id,
            ),
        )
        _ = edge
        reversed_chain.append(parent.id)
        current = parent.id
    reversed_chain.reverse()
    return reversed_chain


def _chain_weight(world: World, chain: list[int]) -> float:
    total = 0.0
    for source, target in zip(chain, chain[1:], strict=False):
        for edge in world.provenance.edges.values():
            if edge.source_node_id == source and edge.target_node_id == target:
                total += edge.weight
                break
    return total


class _Canvas:
    def __init__(self, width: int, height: int, *, background: Color = (0, 0, 0, 0)) -> None:
        self.width = width
        self.height = height
        self.pixels = [bytearray(background * width) for _ in range(height)]

    def blend_pixel(self, x: int, y: int, color: Color) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        r, g, b, a = color
        if a <= 0:
            return
        row = self.pixels[y]
        offset = x * 4
        br, bg, bb, ba = row[offset : offset + 4]
        src_a = a / 255.0
        dst_a = ba / 255.0
        out_a = src_a + dst_a * (1.0 - src_a)
        if out_a <= 0.0:
            row[offset : offset + 4] = bytes((0, 0, 0, 0))
            return
        out_r = int((r * src_a + br * dst_a * (1.0 - src_a)) / out_a)
        out_g = int((g * src_a + bg * dst_a * (1.0 - src_a)) / out_a)
        out_b = int((b * src_a + bb * dst_a * (1.0 - src_a)) / out_a)
        row[offset : offset + 4] = bytes((out_r, out_g, out_b, int(out_a * 255)))

    def fill_rect(self, x0: int, y0: int, width: int, height: int, color: Color) -> None:
        for y in range(y0, y0 + height):
            for x in range(x0, x0 + width):
                self.blend_pixel(x, y, color)

    def draw_line(self, start: Coord, end: Coord, color: Color, *, thickness: int = 1) -> None:
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy

        while True:
            half = max(0, thickness // 2)
            for ox in range(-half, half + 1):
                for oy in range(-half, half + 1):
                    self.blend_pixel(x0 + ox, y0 + oy, color)
            if x0 == x1 and y0 == y1:
                break
            error2 = 2 * error
            if error2 >= dy:
                error += dy
                x0 += sx
            if error2 <= dx:
                error += dx
                y0 += sy

    def to_bytes(self) -> bytes:
        return b"".join(bytes([0]) + bytes(row) for row in self.pixels)


def _render_substrate(world: World, *, cell_size: int) -> tuple[int, int, bytes]:
    canvas = _Canvas(world.size * cell_size, world.size * cell_size, background=(0, 0, 0, 255))
    biome_colors = {
        "Ocean": (36, 84, 156),
        "Alpine": (210, 214, 220),
        "Forest": (54, 122, 62),
        "Dryland": (181, 152, 82),
        "Lowland": (124, 164, 94),
    }
    for (x, y), tile in world.baseline.items():
        base = biome_colors.get(tile.biome, (128, 128, 128))
        shade = 0.55 + max(0.0, tile.elevation + 1.0) * 0.25 + tile.water_flow * 0.20
        color = (
            _clamp_byte(base[0] * shade),
            _clamp_byte(base[1] * shade),
            _clamp_byte(base[2] * shade),
            255,
        )
        _fill_tile(canvas, x, y, cell_size, color)
    return canvas.width, canvas.height, canvas.to_bytes()


def _render_resources(world: World, *, cell_size: int) -> tuple[int, int, bytes]:
    canvas = _Canvas(world.size * cell_size, world.size * cell_size)
    for (x, y), tile in world.baseline.items():
        timber = _scale_alpha(tile.timber, 180)
        iron = _scale_alpha(tile.iron, 190)
        coal = _scale_alpha(tile.coal, 170)
        if timber:
            _fill_tile(canvas, x, y, cell_size, (34, 200, 80, timber))
        if iron:
            _fill_tile(canvas, x, y, cell_size, (232, 120, 52, iron))
        if coal:
            _fill_tile(canvas, x, y, cell_size, (148, 118, 210, coal))
    return canvas.width, canvas.height, canvas.to_bytes()


def _render_entities(world: World, *, cell_size: int) -> tuple[int, int, bytes]:
    canvas = _Canvas(world.size * cell_size, world.size * cell_size)
    entity_colors = {
        EntityType.SETTLEMENT: (255, 235, 90, 235),
        EntityType.LUMBER_CAMP: (50, 220, 120, 235),
        EntityType.MINE: (255, 150, 70, 235),
        EntityType.ROAD: (245, 245, 245, 200),
        EntityType.FORT: (250, 90, 90, 240),
        EntityType.RUIN: (170, 170, 170, 220),
        EntityType.BATTLEFIELD: (180, 60, 180, 220),
    }
    for entity in sorted(world.entities.values(), key=lambda candidate: candidate.id):
        color = entity_colors.get(entity.type, (255, 255, 255, 220))
        if entity.type == EntityType.ROAD:
            points = [_tile_center(coord, cell_size) for coord in entity.coordinates]
            for start, end in zip(points, points[1:], strict=False):
                canvas.draw_line(start, end, color, thickness=max(1, cell_size // 2))
            continue
        for coord in entity.coordinates:
            _fill_tile(canvas, coord[0], coord[1], cell_size, color)
    return canvas.width, canvas.height, canvas.to_bytes()


def _render_causal_chain(world: World, chain: list[int], *, cell_size: int) -> tuple[int, int, bytes]:
    canvas = _Canvas(world.size * cell_size, world.size * cell_size)
    if not chain:
        return canvas.width, canvas.height, canvas.to_bytes()

    centers: list[Coord] = []
    for index, node_id in enumerate(chain):
        intensity = 110 + min(120, index * 18)
        color = (255, intensity, 70, 235)
        coords = list(_node_footprint(world, node_id))
        if not coords:
            continue
        for coord in coords:
            _fill_tile(canvas, coord[0], coord[1], cell_size, color)
        centers.append(_footprint_center(coords, cell_size))

    for start, end in zip(centers, centers[1:], strict=False):
        canvas.draw_line(start, end, (255, 80, 80, 255), thickness=max(1, cell_size // 2))
    return canvas.width, canvas.height, canvas.to_bytes()


def _node_footprint(world: World, node_id: int) -> Iterable[Coord]:
    node = world.provenance.nodes[node_id]
    if node.entity_id is not None:
        yield from world.entities[node.entity_id].coordinates
        return

    coord = node.payload.get("coord")
    if _is_coord(coord):
        yield coord
        return

    road_entity = node.payload.get("road_entity")
    if isinstance(road_entity, int) and road_entity in world.entities:
        yield from world.entities[road_entity].coordinates
        return

    start_entity = node.payload.get("start_entity")
    end_entity = node.payload.get("end_entity")
    if isinstance(start_entity, int) and start_entity in world.entities:
        yield from world.entities[start_entity].coordinates[:1]
    if isinstance(end_entity, int) and end_entity in world.entities:
        yield from world.entities[end_entity].coordinates[:1]


def _fill_tile(canvas: _Canvas, x: int, y: int, cell_size: int, color: Color) -> None:
    canvas.fill_rect(x * cell_size, y * cell_size, cell_size, cell_size, color)


def _tile_center(coord: Coord, cell_size: int) -> Coord:
    x, y = coord
    return (x * cell_size + cell_size // 2, y * cell_size + cell_size // 2)


def _footprint_center(coords: list[Coord], cell_size: int) -> Coord:
    avg_x = sum(coord[0] for coord in coords) / len(coords)
    avg_y = sum(coord[1] for coord in coords) / len(coords)
    return (
        int(avg_x * cell_size + cell_size / 2),
        int(avg_y * cell_size + cell_size / 2),
    )


def _is_coord(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(component, int) for component in value)
    )


def _scale_alpha(value: float, limit: int) -> int:
    return _clamp_byte(value * limit)


def _clamp_byte(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _write_png(path: Path, image: tuple[int, int, bytes]) -> None:
    width, height, raw_bytes = image
    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,
        6,
        0,
        0,
        0,
    )
    compressed = zlib.compress(raw_bytes, level=9)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )
