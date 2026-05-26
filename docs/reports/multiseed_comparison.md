# Gate 5 Multi-Seed Comparison Report

- seed count: `5`
- seeds: `7, 11, 13, 17, 19`
- size: `64`
- scope: Worldline vs Control C under timber perturbation and route-cut/battlefield perturbation only

## Timber Perturbation: Worldline vs Control C

| Aggregate Metric | Worldline | Control C |
| --- | --- | --- |
| Post-perturbation pass rate | 5/5 (1.00) | 0/5 (0.00) |
| Compaction retention pass rate | 5/5 (1.00) | 0/5 (0.00) |
| Mean perturbation consequence rate | 1.00 | 1.00 |
| Mean contradiction count | 0.00 | 2.00 |
| Mean explanation depth | 24.00 | 5.00 |

### Timber Reading

- Aggregate pass rates: post-perturbation Worldline=5/5 (1.00), Control C=0/5 (0.00); compaction Worldline=5/5 (1.00), Control C=0/5 (0.00).
- Aggregate contradiction gap (Control C - Worldline): mean=2.00, total=10.
- Aggregate perturbation consequence rate: Worldline=1.00, Control C=1.00.

## Route-Cut / Battlefield: Worldline vs Control C

| Aggregate Metric | Worldline | Control C |
| --- | --- | --- |
| Post-perturbation pass rate | 5/5 (1.00) | 0/5 (0.00) |
| Compaction retention pass rate | 5/5 (1.00) | 0/5 (0.00) |
| Mean perturbation consequence rate | 1.00 | 1.00 |
| Mean contradiction count | 0.00 | 3.00 |
| Mean explanation depth | 12.00 | 5.00 |

### Route-Cut Reading

- Aggregate pass rates: post-perturbation Worldline=5/5 (1.00), Control C=0/5 (0.00); compaction Worldline=5/5 (1.00), Control C=0/5 (0.00).
- Aggregate contradiction gap (Control C - Worldline): mean=3.00, total=15.
- Aggregate perturbation consequence rate: Worldline=1.00, Control C=1.00.

## Limitations

- This report is a small deterministic five-seed executable comparison, not a bandwidth sweep or distributional study.
- Control C is a plausible post-hoc baseline, not a learned competitor or a strongest possible symbolic protocol.
- Causal-validity flags are proxy checks over explanation structure and retained provenance markers, not a full proof system.
- No claim is made here about superiority over structured-text baselines relative to the Oracle condition; that remains a separate requirement.
