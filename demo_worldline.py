"""First Worldline Projection demo target.

Run:
    python demo_worldline.py --seed 12345 --size 128
"""

from __future__ import annotations

import argparse

from worldline.debug_render import render_debug_overlays
from worldline.generate import generate_world
from worldline.models import EntityType
from worldline.perturb import compact_timber_collapse, find_timber_dependency_pair, inject_timber_destruction
from worldline.query import explain_entity
from worldline.validate import run_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--debug-output-dir", type=str, default=None)
    parser.add_argument("--debug-cell-size", type=int, default=4)
    args = parser.parse_args()

    world = generate_world(seed=args.seed, size=args.size)

    print("WORLDLINE PROJECTION DEMO")
    print(f"seed={world.seed} size={world.size}")
    print()

    settlements = [entity for entity in world.entities.values() if entity.type == EntityType.SETTLEMENT]
    settlement_id, _ = find_timber_dependency_pair(world)

    print("BEFORE")
    for settlement in settlements[:5]:
        print(explain_entity(world, settlement.id))
        print()

    perturbation = inject_timber_destruction(world, magnitude=0.9, t=100)
    print("PERTURBATION")
    print(f"{perturbation.type} id={perturbation.id} magnitude={perturbation.magnitude}")
    print()

    print("AFTER RESOLUTION")
    print(explain_entity(world, settlement_id))
    print()

    archive_id = compact_timber_collapse(world, t=142)
    print("AFTER COMPACTION")
    print(f"archive_node={archive_id}")
    print(explain_entity(world, settlement_id))
    print()

    print("VALIDATION")
    for result in run_validation(world):
        marker = "PASS" if result.passed else "FAIL"
        print(f"{marker}: {result.name} — {result.details}")

    if args.debug_output_dir:
        overlays = render_debug_overlays(
            world,
            args.debug_output_dir,
            cell_size=args.debug_cell_size,
            chain_entity_id=settlement_id,
        )
        print()
        print("DEBUG OVERLAYS")
        print(f"substrate={overlays.substrate}")
        print(f"resources={overlays.resources}")
        print(f"entities={overlays.entities}")
        print(f"causal_chain={overlays.causal_chain}")


if __name__ == "__main__":
    main()
