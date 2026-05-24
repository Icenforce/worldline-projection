"""First Worldline Projection demo target.

Run:
    python demo_worldline.py --seed 12345 --size 128
"""

from __future__ import annotations

import argparse

from worldline.generate import generate_world
from worldline.perturb import compact_timber_collapse, inject_timber_destruction
from worldline.query import explain_entity
from worldline.validate import run_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()

    world = generate_world(seed=args.seed, size=args.size)

    print("WORLDLINE PROJECTION DEMO")
    print(f"seed={world.seed} size={world.size}")
    print()

    print("BEFORE")
    print(explain_entity(world, 1))
    print()

    perturbation = inject_timber_destruction(world, magnitude=0.9, t=100)
    print("PERTURBATION")
    print(f"{perturbation.type} id={perturbation.id} magnitude={perturbation.magnitude}")
    print()

    print("AFTER RESOLUTION")
    print(explain_entity(world, 1))
    print()

    archive_id = compact_timber_collapse(world, t=142)
    print("AFTER COMPACTION")
    print(f"archive_node={archive_id}")
    print(explain_entity(world, 1))
    print()

    print("VALIDATION")
    for result in run_validation(world):
        marker = "PASS" if result.passed else "FAIL"
        print(f"{marker}: {result.name} — {result.details}")


if __name__ == "__main__":
    main()
