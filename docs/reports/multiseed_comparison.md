# Gate 5 Multi-Seed Comparison Report

- seed count: `5`
- seeds: `7, 11, 13, 17, 19`
- size: `64`
- scope: Worldline vs Controls A/B/C under timber perturbation and route-cut/battlefield perturbation only

## Timber Perturbation: Worldline vs Controls A/B/C

| Aggregate Metric | Worldline | Control A | Control B | Control C |
| --- | --- | --- | --- | --- |
| Mean explanation depth | 24.00 | 4.00 | 6.00 | 5.00 |
| Mean contradiction count | 0.00 | 2.00 | 1.00 | 2.00 |
| Mean perturbation consequence rate | 1.00 | 1.00 | 1.00 | 1.00 |
| Compaction explanation retention pass rate | 5/5 (1.00) | 0/5 (0.00) | 0/5 (0.00) | 0/5 (0.00) |

### Timber Reading

- Control A: contradiction gap mean=2.00, depth=4.00, compaction retention=0/5 (0.00).
- Control B: contradiction gap mean=1.00, depth=6.00, compaction retention=0/5 (0.00).
- Control C: contradiction gap mean=2.00, depth=5.00, compaction retention=0/5 (0.00).
- Worldline reference: depth=24.00, contradictions=0.00, compaction retention=5/5 (1.00).

## Route-Cut / Battlefield: Worldline vs Controls A/B/C

| Aggregate Metric | Worldline | Control A | Control B | Control C |
| --- | --- | --- | --- | --- |
| Mean explanation depth | 12.00 | 4.00 | 6.00 | 5.00 |
| Mean contradiction count | 0.00 | 2.00 | 2.00 | 3.00 |
| Mean perturbation consequence rate | 1.00 | 1.00 | 1.00 | 1.00 |
| Compaction explanation retention pass rate | 5/5 (1.00) | 0/5 (0.00) | 0/5 (0.00) | 0/5 (0.00) |

### Route-Cut / Battlefield Reading

- Control A: contradiction gap mean=2.00, depth=4.00, compaction retention=0/5 (0.00).
- Control B: contradiction gap mean=2.00, depth=6.00, compaction retention=0/5 (0.00).
- Control C: contradiction gap mean=3.00, depth=5.00, compaction retention=0/5 (0.00).
- Worldline reference: depth=12.00, contradictions=0.00, compaction retention=5/5 (1.00).

## Limitations

- This report is a small deterministic five-seed executable comparison, not a bandwidth sweep or distributional study.
- Control A is intentionally random and uncoupled; it is expected to fail because it lacks coherent placement and provenance.
- Control B is intentionally heuristic and spatially plausible; it is expected to fail because it lacks executable provenance and post-compaction causal retention.
- Control C remains the strongest post-hoc explanation opponent in this slice.
- No claim is made here about superiority over structured-text baselines relative to the Oracle condition; that remains a separate requirement.
