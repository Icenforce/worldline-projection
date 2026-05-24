# Worldline Projection v0.3 — Implementation Contract

**Project type:** causal-provenance procedural generation testbed  
**Status:** implementation contract draft  
**Primary target:** first Python prototype  
**Core discipline:** no claim survives unless it can become data, code, a validation test, or a falsifiable design constraint.

## 1. Project mandate

Worldline Projection is a procedural generation testbed for causal accountability.

Its purpose is to determine whether generated worlds become measurably more coherent and more useful when entities are produced with explicit causal ancestry, and when player actions propagate through typed dependency structures rather than through full continuous simulation.

The project is not trying to generate infinite worlds. It is trying to generate worlds where local details can answer a meaningful question:

> Why is this here, and what happens if its causes change?

The core claim is not that deterministic generation is novel. The core claim is that **explanation graphs can become executable dependency structures**.

A provenance graph that only explains is lore.  
A provenance graph that also breaks, degrades, reroutes, repairs, invalidates, and survives compaction is architecture.

## 2. Non-goals

The first prototype explicitly excludes 3D graphics, sprites, visual polish, UI design, NPC simulation, combat, dialogue, LLM-generated lore, full economic simulation, full historical simulation, artifact/item-level provenance, real-time frame-loop integration, save-file replacement, and universal world-generation claims.

The prototype is allowed to output only arrays, tables, graph records, validation reports, and text-based query explanations.

## 3. First proof scenario

The first successful demonstration must:

1. Generate a deterministic 2D world from seed `12345`.
2. Print five generated settlements and their structural explanations.
3. Select one settlement dependent on timber.
4. Destroy or severely degrade its supporting forest through a perturbation.
5. Resolve downstream consequences.
6. Print the changed settlement state.
7. Compact the affected region.
8. Query the settlement again.
9. Confirm that the explanation still preserves the causal reason for decline after compaction.
10. Run validation.
11. Generate negative-control worlds.
12. Compare explanation depth, contradiction count, perturbation consequence, and explanation retention.

## 4. Core success criterion

Worldline succeeds only if the same causal structure used to explain an entity is also used to modify that entity when upstream conditions change.

A system that merely explains generated placement after the fact is not Worldline.

A system that stores causal dependencies but does not use them for consequence propagation is not Worldline.

A system that compacts state but erases causal explanation is not Worldline.

## 5. Entity scope for v0.3

Supported entities:

- `Settlement`
- `Road`
- `Mine`
- `LumberCamp`
- `Fort`
- `Ruin`
- `Battlefield`

No generic `ResourceSite` entity is allowed.

Raw resources such as timber, iron, and coal are substrate fields, not entities.

Artifacts are postponed until settlement/resource/history provenance is proven.

## 6. Causal edge types

The allowed edge types for v0.3 are:

- `REQUIRES`
- `ENABLES`
- `SUPPLIES`
- `TRANSITS`
- `LOCATES`
- `CAUSES`
- `DAMAGES`
- `INVALIDATES`
- `REPLACES`
- `REPAIRS`
- `DESCENDS_FROM`

A provenance edge is valid only if it is load-bearing. An edge is load-bearing if damaging/removing the source changes target state, determines target location, determines target type/subtype, is required by a typed invariant, or appears in a compacted causal archive that previously satisfied those conditions.

## 7. Compaction law

Compaction reduces operational load. It must not erase causal truth.

> Compress operational load, not explanatory truth.

Compaction must output:

1. `LocalBaselinePatch`
2. `CompactionArchiveEvent` provenance node
3. rewritten or additional provenance edges from affected entities to the archive event
4. causal summary payload preserving differential weights, temporal order, and spatial scope

After compaction, the query engine must still answer why an affected entity changed.

## 8. Negative controls

Worldline must be compared against:

1. random uncoupled generation,
2. heuristic coherent generation,
3. heuristic coherent generation with post-hoc explanation templates.

Control C is the serious opponent. Worldline must beat it after perturbation and compaction.

## 9. Acceptance gates

1. Deterministic substrate: same seed produces byte-identical substrate arrays.
2. Accountable entity placement: generated entities have subtype-appropriate load-bearing provenance.
3. Baseline query explanations: the query engine can explain generated entities.
4. Perturbation propagation: damaging an upstream dependency changes dependent entities or produces explicit resilience/no-impact explanation.
5. Compaction without amnesia: affected entities retain causally meaningful explanations after compaction.
6. Negative-control comparison: Worldline beats Control C on post-perturbation explanation validity and compaction retention.

## 10. Immediate implementation target

The first code milestone is the timber-collapse proof scenario:

```text
BEFORE:
Settlement_12 depends on LumberCamp_04, which supplies timber from high-timber basin cells.

PERTURBATION:
ResourceDestruction damages timber field in Chunk_3_5 by 0.90 magnitude.

AFTER RESOLUTION:
LumberCamp_04 function drops.
Settlement_12 wealth drops.
Settlement_12 status changes from Stable to Poor.

AFTER COMPACTION:
Settlement_12 remains Poor because CompactionArchiveEvent_212 preserves the timber collapse and records dependency_loss for Settlement_12.

VALIDATION:
Compaction explanation retention: PASS.
```
