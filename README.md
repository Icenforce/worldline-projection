# Worldline Projection

**Worldline Projection** is a causal-provenance procedural generation testbed.

Its purpose is to determine whether generated worlds become more coherent and more useful when entities are produced with explicit causal ancestry, and when player actions propagate through typed dependency structures rather than through full continuous simulation.

The central question is:

> Why is this here, and what happens if its causes change?

Worldline is not a game engine, not a lore generator, and not a universal world generator. It is a small, falsifiable prototype for testing whether explanation graphs can become executable dependency structures.

## Core thesis

A provenance graph that only explains is lore.

A provenance graph that also breaks, degrades, reroutes, repairs, invalidates, and survives compaction is architecture.

Worldline succeeds only if the same causal structure used to explain an entity is also used to modify that entity when upstream conditions change.

## First proof scenario

The first successful demo must:

1. Generate a deterministic 2D world from seed `12345`.
2. Print several settlements and their structural explanations.
3. Select one settlement dependent on timber.
4. Damage its supporting timber field through a perturbation.
5. Resolve downstream effects.
6. Compact the affected region.
7. Query the settlement again.
8. Confirm that the explanation still preserves the causal reason for decline after compaction.
9. Compare against heuristic and post-hoc explanation controls.

## Current scope

The v0.3 prototype is intentionally narrow:

- 2D grid only.
- Text/table/graph output only.
- No graphics.
- No NPC simulation.
- No artifacts.
- No LLM-generated lore.
- No real-time game loop.

Supported v0.3 entity types:

- `Settlement`
- `Road`
- `Mine`
- `LumberCamp`
- `Fort`
- `Ruin`
- `Battlefield`

Raw resources such as timber, iron, and coal are substrate fields, not entities.

## Repository layout

```text
docs/                         Project contracts and design notes
tests/                         Validation tests
demo_worldline.py              Main prototype implementation and CLI demo
pyproject.toml                 Project metadata and dev dependencies
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python demo_worldline.py --seed 12345 --size 128
pytest
```

## Latest diagnostic overlays

These are diagnostic overlays, not the visual/game renderer.

Latest committed debug renders:
- [substrate](docs/debug/latest/substrate.png)
- [resources](docs/debug/latest/resources.png)
- [entities](docs/debug/latest/entities.png)
- [causal chain](docs/debug/latest/causal_chain.png)

Recommended local regeneration command:

```bash
python demo_worldline.py --seed 12345 --size 128 --debug-output-dir docs/debug/latest --debug-cell-size 4
```

Autonomous workflow policy for implementation passes:
1. Start from a clean tree.
2. Make one scoped implementation/test change set.
3. Run `pytest`.
4. Regenerate `docs/debug/latest/` with the command above.
5. Check `git status`.
6. If the PNGs changed for an understood world/render logic reason, commit them with the related code change.
7. If the PNGs changed unexpectedly, explain the cause before proceeding.
8. Do not continue unrelated work on a dirty tree.

Constraints:
- Keep only the latest PNG set in `docs/debug/latest/`.
- Do not create timestamped render archives.
- Debug rendering must remain read-only and must not mutate world state, provenance, perturbations, or validation results.
- Do not treat these overlays as game rendering, UI rendering, or a visual-layer architecture.

The current prototype already covers the deterministic substrate, accountable placement for settlements/resources/roads/forts/ruins/battlefields, the timber-collapse perturbation path, route-cut perturbation coverage, generalized compaction retention checks for the current proof paths, and the initial negative-control comparison against Control C. Remaining contract work is mainly broader gate-audit closure and validation hardening beyond the current proof paths.
