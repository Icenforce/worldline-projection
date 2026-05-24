"""Deterministic substrate generation for Worldline Projection.

The substrate phase is intentionally independent of entities and provenance. It creates
an immutable natural field that later systems must explain against rather than mutate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from worldline.models import BaselineTile

Coord = tuple[int, int]


@dataclass(frozen=True)
class SubstrateArrays:
    elevation: list[list[float]]
    slope: list[list[float]]
    water_flow: list[list[float]]
    basin_id: list[list[int]]
    fertility: list[list[float]]
    timber: list[list[float]]
    iron: list[list[float]]
    coal: list[list[float]]


def generate_substrate(seed: int, size: int) -> dict[Coord, BaselineTile]:
    """Generate immutable seed-derived natural substrate tiles.

    This is a lightweight deterministic approximation, not a physical simulator. The goal
    for Gate 1 is reproducibility and layered dependence:

    elevation -> slope -> hydrology/basins -> fertility/biomes -> resources
    """

    if size < 16:
        raise ValueError("size must be at least 16")

    arrays = generate_substrate_arrays(seed=seed, size=size)
    tiles: dict[Coord, BaselineTile] = {}

    for x in range(size):
        for y in range(size):
            elevation = arrays.elevation[x][y]
            water = arrays.water_flow[x][y]
            timber = arrays.timber[x][y]
            biome = classify_biome(
                elevation=elevation,
                water_flow=water,
                fertility=arrays.fertility[x][y],
                timber=timber,
            )
            tiles[(x, y)] = BaselineTile(
                x=x,
                y=y,
                elevation=elevation,
                slope=arrays.slope[x][y],
                water_flow=water,
                basin_id=arrays.basin_id[x][y],
                biome=biome,
                fertility=arrays.fertility[x][y],
                timber=timber,
                iron=arrays.iron[x][y],
                coal=arrays.coal[x][y],
            )

    return tiles


def generate_substrate_arrays(seed: int, size: int) -> SubstrateArrays:
    elevation = generate_elevation(seed=seed, size=size)
    slope = calculate_slope(elevation)
    water_flow = calculate_water_flow(elevation=elevation, size=size)
    basin_id = assign_basins(elevation=elevation, size=size)
    fertility = calculate_fertility(elevation=elevation, slope=slope, water_flow=water_flow)
    timber = calculate_timber(seed=seed, elevation=elevation, fertility=fertility, slope=slope)
    iron = calculate_mineral(seed=seed + 101, elevation=elevation, slope=slope, preferred="highland")
    coal = calculate_mineral(seed=seed + 202, elevation=elevation, slope=slope, preferred="midland")
    return SubstrateArrays(
        elevation=elevation,
        slope=slope,
        water_flow=water_flow,
        basin_id=basin_id,
        fertility=fertility,
        timber=timber,
        iron=iron,
        coal=coal,
    )


def generate_elevation(seed: int, size: int) -> list[list[float]]:
    rng = random.Random(seed)
    phases = [rng.uniform(0, math.tau) for _ in range(6)]
    frequencies = [1.0, 2.0, 3.0, 5.0]
    weights = [0.45, 0.25, 0.18, 0.12]

    field = [[0.0 for _ in range(size)] for _ in range(size)]
    for x in range(size):
        nx = x / max(1, size - 1)
        for y in range(size):
            ny = y / max(1, size - 1)
            value = 0.0
            for index, (frequency, weight) in enumerate(zip(frequencies, weights, strict=True)):
                value += weight * math.sin((nx * frequency * math.tau) + phases[index])
                value += weight * math.cos((ny * frequency * math.tau) + phases[index + 2])
            # Continental bias: low coasts, higher central mass.
            dx = abs(nx - 0.5)
            dy = abs(ny - 0.5)
            continental = 1.0 - min(1.0, math.sqrt(dx * dx + dy * dy) * 1.7)
            value = 0.58 * value + 0.42 * continental
            field[x][y] = value

    return normalize_field(field, out_min=-1.0, out_max=1.0)


def calculate_slope(elevation: list[list[float]]) -> list[list[float]]:
    size = len(elevation)
    slope = [[0.0 for _ in range(size)] for _ in range(size)]
    for x in range(size):
        for y in range(size):
            left = elevation[max(0, x - 1)][y]
            right = elevation[min(size - 1, x + 1)][y]
            down = elevation[x][max(0, y - 1)]
            up = elevation[x][min(size - 1, y + 1)]
            gradient = math.sqrt((right - left) ** 2 + (up - down) ** 2) / 2.0
            slope[x][y] = clamp(gradient, 0.0, 1.0)
    return slope


def calculate_water_flow(elevation: list[list[float]], size: int) -> list[list[float]]:
    """Approximate water accumulation using downhill routing from high to low cells."""

    flow = [[0.0 for _ in range(size)] for _ in range(size)]
    cells = [(elevation[x][y], x, y) for x in range(size) for y in range(size)]
    cells.sort(reverse=True)

    for _, x, y in cells:
        # rainfall bias: highlands generate runoff, seas do not.
        if elevation[x][y] > -0.05:
            flow[x][y] += 1.0 + max(0.0, elevation[x][y])
        target = lowest_neighbor(elevation, x, y)
        if target is not None:
            tx, ty = target
            if elevation[tx][ty] < elevation[x][y]:
                flow[tx][ty] += flow[x][y] * 0.92

    return normalize_field(flow, out_min=0.0, out_max=1.0)


def assign_basins(elevation: list[list[float]], size: int) -> list[list[int]]:
    """Assign coarse basin IDs by following downhill flow to a sink/edge zone."""

    sink_to_id: dict[Coord, int] = {}
    basins = [[0 for _ in range(size)] for _ in range(size)]

    for x in range(size):
        for y in range(size):
            sink = trace_sink(elevation, x, y)
            if sink not in sink_to_id:
                sink_to_id[sink] = len(sink_to_id) + 1
            basins[x][y] = sink_to_id[sink]
    return basins


def trace_sink(elevation: list[list[float]], x: int, y: int) -> Coord:
    size = len(elevation)
    current = (x, y)
    visited: set[Coord] = set()
    for _ in range(size * 2):
        if current in visited:
            return current
        visited.add(current)
        cx, cy = current
        nxt = lowest_neighbor(elevation, cx, cy)
        if nxt is None:
            return current
        nx, ny = nxt
        if elevation[nx][ny] >= elevation[cx][cy]:
            return current
        current = nxt
    return current


def lowest_neighbor(elevation: list[list[float]], x: int, y: int) -> Coord | None:
    size = len(elevation)
    candidates: list[Coord] = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx = x + dx
        ny = y + dy
        if 0 <= nx < size and 0 <= ny < size:
            candidates.append((nx, ny))
    if not candidates:
        return None
    return min(candidates, key=lambda coord: elevation[coord[0]][coord[1]])


def calculate_fertility(
    *,
    elevation: list[list[float]],
    slope: list[list[float]],
    water_flow: list[list[float]],
) -> list[list[float]]:
    size = len(elevation)
    fertility = [[0.0 for _ in range(size)] for _ in range(size)]
    for x in range(size):
        for y in range(size):
            if elevation[x][y] < -0.1:
                fertility[x][y] = 0.0
                continue
            lowland_bonus = 1.0 - clamp((elevation[x][y] + 0.1) / 1.1, 0.0, 1.0)
            slope_penalty = 1.0 - clamp(slope[x][y] * 4.0, 0.0, 1.0)
            water_bonus = math.sqrt(water_flow[x][y])
            fertility[x][y] = clamp(0.45 * water_bonus + 0.35 * lowland_bonus + 0.20 * slope_penalty, 0.0, 1.0)
    return fertility


def calculate_timber(
    *,
    seed: int,
    elevation: list[list[float]],
    fertility: list[list[float]],
    slope: list[list[float]],
) -> list[list[float]]:
    rng = random.Random(seed + 303)
    size = len(elevation)
    timber = [[0.0 for _ in range(size)] for _ in range(size)]
    for x in range(size):
        for y in range(size):
            if elevation[x][y] < -0.05:
                timber[x][y] = 0.0
                continue
            noise = rng.uniform(0.75, 1.15)
            hill_forest_bonus = 0.25 if 0.05 < elevation[x][y] < 0.65 else 0.0
            timber[x][y] = clamp((fertility[x][y] * 0.75 + hill_forest_bonus - slope[x][y] * 0.5) * noise, 0.0, 1.0)
    return timber


def calculate_mineral(
    *,
    seed: int,
    elevation: list[list[float]],
    slope: list[list[float]],
    preferred: str,
) -> list[list[float]]:
    rng = random.Random(seed)
    size = len(elevation)
    mineral = [[0.0 for _ in range(size)] for _ in range(size)]

    centers = [(rng.randrange(size), rng.randrange(size), rng.uniform(0.08, 0.18)) for _ in range(8)]
    for x in range(size):
        for y in range(size):
            if elevation[x][y] < -0.05:
                continue
            if preferred == "highland":
                terrain_bias = clamp((elevation[x][y] + slope[x][y]) / 1.7, 0.0, 1.0)
            else:
                terrain_bias = clamp((0.8 - abs(elevation[x][y] - 0.25)) * 0.7 + slope[x][y], 0.0, 1.0)

            blob = 0.0
            for cx, cy, radius in centers:
                distance = math.sqrt(((x - cx) / size) ** 2 + ((y - cy) / size) ** 2)
                blob = max(blob, clamp(1.0 - distance / radius, 0.0, 1.0))
            mineral[x][y] = clamp(blob * terrain_bias, 0.0, 1.0)
    return mineral


def classify_biome(*, elevation: float, water_flow: float, fertility: float, timber: float) -> str:
    if elevation < -0.1:
        return "Ocean"
    if elevation > 0.72:
        return "Alpine"
    if timber > 0.55:
        return "Forest"
    if fertility < 0.18 and water_flow < 0.15:
        return "Dryland"
    return "Lowland"


def normalize_field(field: list[list[float]], *, out_min: float, out_max: float) -> list[list[float]]:
    flat = [value for column in field for value in column]
    current_min = min(flat)
    current_max = max(flat)
    if math.isclose(current_min, current_max):
        midpoint = (out_min + out_max) / 2.0
        return [[midpoint for _ in column] for column in field]

    scale = (out_max - out_min) / (current_max - current_min)
    return [[out_min + (value - current_min) * scale for value in column] for column in field]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
