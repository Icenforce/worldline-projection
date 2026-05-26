"""Executable Gate 5 comparison report generator."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from pathlib import Path

from worldline.negative_controls import (
    NegativeControlComparison,
    compare_worldline_vs_control_a,
    compare_worldline_vs_control_a_route_cut,
    compare_worldline_vs_control_b,
    compare_worldline_vs_control_b_route_cut,
    compare_worldline_vs_control_c,
    compare_worldline_vs_control_c_route_cut,
)

DEFAULT_COMPARISON_SEEDS: tuple[int, ...] = (7, 11, 13, 17, 19)
CONTROL_ORDER: tuple[str, ...] = ("A", "B", "C")


def render_comparison_report(*, seeds: Sequence[int] | None = None, size: int = 64) -> str:
    ordered_seeds = _normalize_seeds(seeds)
    timber = {
        "A": [compare_worldline_vs_control_a(seed=seed, size=size) for seed in ordered_seeds],
        "B": [compare_worldline_vs_control_b(seed=seed, size=size) for seed in ordered_seeds],
        "C": [compare_worldline_vs_control_c(seed=seed, size=size) for seed in ordered_seeds],
    }
    route_cut = {
        "A": [compare_worldline_vs_control_a_route_cut(seed=seed, size=size) for seed in ordered_seeds],
        "B": [compare_worldline_vs_control_b_route_cut(seed=seed, size=size) for seed in ordered_seeds],
        "C": [compare_worldline_vs_control_c_route_cut(seed=seed, size=size) for seed in ordered_seeds],
    }

    lines = [
        "# Gate 5 Multi-Seed Comparison Report",
        "",
        f"- seed count: `{len(ordered_seeds)}`",
        f"- seeds: `{', '.join(str(seed) for seed in ordered_seeds)}`",
        f"- size: `{size}`",
        "- scope: Worldline vs Controls A/B/C under timber perturbation and route-cut/battlefield perturbation only",
        "",
        "## Timber Perturbation: Worldline vs Controls A/B/C",
        "",
        _aggregate_table(timber),
        "",
        _scenario_summary("timber", timber),
        "",
        "## Route-Cut / Battlefield: Worldline vs Controls A/B/C",
        "",
        _aggregate_table(route_cut),
        "",
        _scenario_summary("route-cut / battlefield", route_cut),
        "",
        "## Limitations",
        "",
        "- This report is a small deterministic five-seed executable comparison, not a bandwidth sweep or distributional study.",
        "- Control A is intentionally random and uncoupled; it is expected to fail because it lacks coherent placement and provenance.",
        "- Control B is intentionally heuristic and spatially plausible; it is expected to fail because it lacks executable provenance and post-compaction causal retention.",
        "- Control C remains the strongest post-hoc explanation opponent in this slice.",
        "- No claim is made here about superiority over structured-text baselines relative to the Oracle condition; that remains a separate requirement.",
    ]
    return "\n".join(lines) + "\n"


def write_comparison_report(
    output_path: str | Path,
    *,
    seeds: Sequence[int] | None = None,
    size: int = 64,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_comparison_report(seeds=seeds, size=size), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--seed", type=int, action="append", dest="seeds")
    args = parser.parse_args(argv)

    output = write_comparison_report(args.output, seeds=args.seeds, size=args.size)
    print(output)


def _aggregate_table(comparison_sets: dict[str, Sequence[NegativeControlComparison]]) -> str:
    worldline_reference = comparison_sets["A"]
    count = len(worldline_reference)
    return "\n".join(
        [
            "| Aggregate Metric | Worldline | Control A | Control B | Control C |",
            "| --- | --- | --- | --- | --- |",
            (
                "| Mean explanation depth | "
                f"{_mean(item.worldline_explanation_depth for item in worldline_reference):.2f} | "
                f"{_mean(item.control_explanation_depth for item in comparison_sets['A']):.2f} | "
                f"{_mean(item.control_explanation_depth for item in comparison_sets['B']):.2f} | "
                f"{_mean(item.control_explanation_depth for item in comparison_sets['C']):.2f} |"
            ),
            (
                "| Mean contradiction count | "
                f"{_mean(item.worldline_contradiction_count for item in worldline_reference):.2f} | "
                f"{_mean(item.control_contradiction_count for item in comparison_sets['A']):.2f} | "
                f"{_mean(item.control_contradiction_count for item in comparison_sets['B']):.2f} | "
                f"{_mean(item.control_contradiction_count for item in comparison_sets['C']):.2f} |"
            ),
            (
                "| Mean perturbation consequence rate | "
                f"{_mean(item.worldline_perturbation_consequence_rate for item in worldline_reference):.2f} | "
                f"{_mean(item.control_perturbation_consequence_rate for item in comparison_sets['A']):.2f} | "
                f"{_mean(item.control_perturbation_consequence_rate for item in comparison_sets['B']):.2f} | "
                f"{_mean(item.control_perturbation_consequence_rate for item in comparison_sets['C']):.2f} |"
            ),
            (
                "| Compaction explanation retention pass rate | "
                f"{_pass_rate(sum(item.worldline_compaction_retention_valid for item in worldline_reference), count)} | "
                f"{_pass_rate(sum(item.control_compaction_retention_valid for item in comparison_sets['A']), count)} | "
                f"{_pass_rate(sum(item.control_compaction_retention_valid for item in comparison_sets['B']), count)} | "
                f"{_pass_rate(sum(item.control_compaction_retention_valid for item in comparison_sets['C']), count)} |"
            ),
        ]
    )


def _scenario_summary(label: str, comparison_sets: dict[str, Sequence[NegativeControlComparison]]) -> str:
    worldline_reference = comparison_sets["A"]
    lines = [f"### {label.title()} Reading", ""]
    for control_name in CONTROL_ORDER:
        comparisons = comparison_sets[control_name]
        lines.append(
            "- "
            f"Control {control_name}: contradiction gap mean="
            f"{_mean(item.control_contradiction_count - item.worldline_contradiction_count for item in comparisons):.2f}, "
            f"depth={_mean(item.control_explanation_depth for item in comparisons):.2f}, "
            f"compaction retention={_fraction(sum(item.control_compaction_retention_valid for item in comparisons), len(comparisons))}."
        )
    lines.append(
        "- Worldline reference: "
        f"depth={_mean(item.worldline_explanation_depth for item in worldline_reference):.2f}, "
        f"contradictions={_mean(item.worldline_contradiction_count for item in worldline_reference):.2f}, "
        f"compaction retention={_fraction(sum(item.worldline_compaction_retention_valid for item in worldline_reference), len(worldline_reference))}."
    )
    return "\n".join(lines)


def _normalize_seeds(seeds: Sequence[int] | None) -> tuple[int, ...]:
    if seeds is None:
        return DEFAULT_COMPARISON_SEEDS
    ordered: list[int] = []
    seen: set[int] = set()
    for seed in seeds:
        if seed in seen:
            continue
        seen.add(seed)
        ordered.append(seed)
    if not ordered:
        raise ValueError("at least one seed is required")
    return tuple(ordered)


def _mean(values: Iterable[float | int]) -> float:
    collected = [float(value) for value in values]
    return sum(collected) / len(collected)


def _fraction(passes: int, total: int) -> str:
    return f"{passes}/{total} ({passes / total:.2f})"


def _pass_rate(passes: int, total: int) -> str:
    return _fraction(passes, total)


if __name__ == "__main__":
    main()
