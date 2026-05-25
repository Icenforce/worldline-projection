# Gate 5 Formal Comparison Report

- seed: `12345`
- size: `128`
- scope: Worldline vs Control C under timber perturbation and route-cut/battlefield perturbation

## Timber Perturbation: Worldline vs Control C

| Metric | Worldline | Control C |
| --- | --- | --- |
| Post-perturbation causal validity | pass | fail |
| Compaction retention validity | pass | fail |
| Contradiction count | 0 | 2 |
| Explanation depth | 24 | 5 |

### Timber Reading

- Worldline preserves a perturbation-linked timber explanation through compaction.
- Control C produces a plausible timber narrative, but it fails the causal-validity check after perturbation.
- Contradiction gap: Worldline=0, Control C=2.

## Route-Cut / Battlefield: Worldline vs Control C

| Metric | Worldline | Control C |
| --- | --- | --- |
| Post-perturbation causal validity | pass | fail |
| Compaction retention validity | pass | fail |
| Contradiction count | 0 | 3 |
| Explanation depth | 12 | 5 |

### Route-Cut Reading

- Worldline retains route-cut / battlefield consequences with executable provenance through compaction.
- Control C can tell a coherent corridor-disruption story, but it still lacks executable dependency edges and retained entity-specific provenance.
- Contradiction gap: Worldline=0, Control C=3.

## Limitations

- This report summarizes fixed-seed executable comparisons only; it is not a bandwidth sweep or distributional study.
- Control C is designed to be a plausible post-hoc baseline, not a learned competitor or a strongest possible symbolic protocol.
- Causal-validity flags are proxy checks over explanation structure and retained provenance markers, not a full proof system.
- No claim is made here about superiority over structured-text baselines relative to the Oracle condition; that remains a separate requirement.
