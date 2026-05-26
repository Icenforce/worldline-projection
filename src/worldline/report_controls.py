"""Executable Gate 5 comparison report generator."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from pathlib import Path

from worldline.negative_controls import (
    NegativeControlComparison,
    compare_worldline_vs_control_c,
    compare_worldline_vs_control_c_route_cut,
)

DEFAULT_COMPARISON_SEEDS: tuple[int, ...] = (7, 11, 13, 17, 19)


def render_comparison_report(*, seeds: Sequence[int] | None = None, size: int = 64) -> str:
    ordered_seeds = _normalize_seeds(seeds)
    timber = [compare_worldline_vs_control_c(seed=seed, size=size) for seed in ordered_seeds]
    route_cut = [compare_worldline_vs_control_c_route_cut(seed=seed, size=size) for seed in ordered_seeds]

    lines = [
        "# Gate 5 Multi-Seed Comparison Report",
        "",
        f"- seed count: `{len(ordered_seeds)}`",
        f"- seeds: `{', '.join(str(seed) for seed in ordered_seeds)}`",
        f"- size: `{size}`",
        "- scope: Worldline vs Control C under timber perturbation and route-cut/battlefield perturbation only",
        "",
        "## Timber Perturbation: Worldline vs Control C",
        "",
        _aggregate_table(timber),
        "",
        _timber_summary(timber),
        "",
        "## Route-Cut / Battlefield: Worldline vs Control C",
        "",
        _aggregate_table(route_cut),
        "",
        _route_cut_summary(route_cut),
        "",
        "## Limitations",
        "",
        "- This report is a small deterministic five-seed executable comparison, not a bandwidth sweep or distributional study.",
        "- Control C is a plausible post-hoc baseline, not a learned competitor or a strongest possible symbolic protocol.",
        "- Causal-validity flags are proxy checks over explanation structure and retained provenance markers, not a full proof system.",
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


def _aggregate_table(comparisons: Sequence[NegativeControlComparison]) -> str:
    count = len(comparisons)
    return "\n".join(
        [
            "| Aggregate Metric | Worldline | Control C |",
            "| --- | --- | --- |",
            (
                "| Post-perturbation pass rate | "
                f"{_pass_rate(sum(item.worldline_post_perturbation_valid for item in comparisons), count)} | "
                f"{_pass_rate(sum(item.control_post_perturbation_valid for item in comparisons), count)} |"
            ),
            (
                "| Compaction retention pass rate | "
                f"{_pass_rate(sum(item.worldline_compaction_retention_valid for item in comparisons), count)} | "
                f"{_pass_rate(sum(item.control_compaction_retention_valid for item in comparisons), count)} |"
            ),
            (
                "| Mean perturbation consequence rate | "
                f"{_mean(item.worldline_perturbation_consequence_rate for item in comparisons):.2f} | "
                f"{_mean(item.control_perturbation_consequence_rate for item in comparisons):.2f} |"
            ),
            (
                "| Mean contradiction count | "
                f"{_mean(item.worldline_contradiction_count for item in comparisons):.2f} | "
                f"{_mean(item.control_contradiction_count for item in comparisons):.2f} |"
            ),
            (
                "| Mean explanation depth | "
                f"{_mean(item.worldline_explanation_depth for item in comparisons):.2f} | "
                f"{_mean(item.control_explanation_depth for item in comparisons):.2f} |"
            ),
        ]
    )


def _timber_summary(comparisons: Sequence[NegativeControlComparison]) -> str:
    return "\n".join(
        [
            "### Timber Reading",
            "",
            (
                "- Aggregate pass rates: "
                f"post-perturbation Worldline={_fraction(sum(item.worldline_post_perturbation_valid for item in comparisons), len(comparisons))}, "
                f"Control C={_fraction(sum(item.control_post_perturbation_valid for item in comparisons), len(comparisons))}; "
                f"compaction Worldline={_fraction(sum(item.worldline_compaction_retention_valid for item in comparisons), len(comparisons))}, "
                f"Control C={_fraction(sum(item.control_compaction_retention_valid for item in comparisons), len(comparisons))}."
            ),
            (
                "- Aggregate contradiction gap (Control C - Worldline): "
                f"mean={_mean(item.control_contradiction_count - item.worldline_contradiction_count for item in comparisons):.2f}, "
                f"total={sum(item.control_contradiction_count - item.worldline_contradiction_count for item in comparisons)}."
            ),
            (
                "- Aggregate perturbation consequence rate: "
                f"Worldline={_mean(item.worldline_perturbation_consequence_rate for item in comparisons):.2f}, "
                f"Control C={_mean(item.control_perturbation_consequence_rate for item in comparisons):.2f}."
            ),
        ]
    )


def _route_cut_summary(comparisons: Sequence[NegativeControlComparison]) -> str:
    return "\n".join(
        [
            "### Route-Cut Reading",
            "",
            (
                "- Aggregate pass rates: "
                f"post-perturbation Worldline={_fraction(sum(item.worldline_post_perturbation_valid for item in comparisons), len(comparisons))}, "
                f"Control C={_fraction(sum(item.control_post_perturbation_valid for item in comparisons), len(comparisons))}; "
                f"compaction Worldline={_fraction(sum(item.worldline_compaction_retention_valid for item in comparisons), len(comparisons))}, "
                f"Control C={_fraction(sum(item.control_compaction_retention_valid for item in comparisons), len(comparisons))}."
            ),
            (
                "- Aggregate contradiction gap (Control C - Worldline): "
                f"mean={_mean(item.control_contradiction_count - item.worldline_contradiction_count for item in comparisons):.2f}, "
                f"total={sum(item.control_contradiction_count - item.worldline_contradiction_count for item in comparisons)}."
            ),
            (
                "- Aggregate perturbation consequence rate: "
                f"Worldline={_mean(item.worldline_perturbation_consequence_rate for item in comparisons):.2f}, "
                f"Control C={_mean(item.control_perturbation_consequence_rate for item in comparisons):.2f}."
            ),
        ]
    )


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
