"""Executable Gate 5 comparison report generator."""

from __future__ import annotations

import argparse
from pathlib import Path

from worldline.negative_controls import (
    NegativeControlComparison,
    compare_worldline_vs_control_c,
    compare_worldline_vs_control_c_route_cut,
)


def render_comparison_report(*, seed: int = 12345, size: int = 128) -> str:
    timber = compare_worldline_vs_control_c(seed=seed, size=size)
    route_cut = compare_worldline_vs_control_c_route_cut(seed=seed, size=size)

    lines = [
        "# Gate 5 Formal Comparison Report",
        "",
        f"- seed: `{seed}`",
        f"- size: `{size}`",
        "- scope: Worldline vs Control C under timber perturbation and route-cut/battlefield perturbation",
        "",
        "## Timber Perturbation: Worldline vs Control C",
        "",
        _comparison_table(timber),
        "",
        _timber_summary(timber),
        "",
        "## Route-Cut / Battlefield: Worldline vs Control C",
        "",
        _comparison_table(route_cut),
        "",
        _route_cut_summary(route_cut),
        "",
        "## Limitations",
        "",
        "- This report summarizes fixed-seed executable comparisons only; it is not a bandwidth sweep or distributional study.",
        "- Control C is designed to be a plausible post-hoc baseline, not a learned competitor or a strongest possible symbolic protocol.",
        "- Causal-validity flags are proxy checks over explanation structure and retained provenance markers, not a full proof system.",
        "- No claim is made here about superiority over structured-text baselines relative to the Oracle condition; that remains a separate requirement.",
    ]
    return "\n".join(lines) + "\n"


def write_comparison_report(output_path: str | Path, *, seed: int = 12345, size: int = 128) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_comparison_report(seed=seed, size=size), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args(argv)

    output = write_comparison_report(args.output, seed=args.seed, size=args.size)
    print(output)


def _comparison_table(comparison: NegativeControlComparison) -> str:
    return "\n".join(
        [
            "| Metric | Worldline | Control C |",
            "| --- | --- | --- |",
            (
                "| Post-perturbation causal validity | "
                f"{_flag(comparison.worldline_post_perturbation_valid)} | "
                f"{_flag(comparison.control_post_perturbation_valid)} |"
            ),
            (
                "| Compaction retention validity | "
                f"{_flag(comparison.worldline_compaction_retention_valid)} | "
                f"{_flag(comparison.control_compaction_retention_valid)} |"
            ),
            (
                "| Contradiction count | "
                f"{comparison.worldline_contradiction_count} | {comparison.control_contradiction_count} |"
            ),
            (
                "| Explanation depth | "
                f"{comparison.worldline_explanation_depth} | {comparison.control_explanation_depth} |"
            ),
        ]
    )


def _timber_summary(comparison: NegativeControlComparison) -> str:
    return "\n".join(
        [
            "### Timber Reading",
            "",
            (
                "- Worldline preserves a perturbation-linked timber explanation through compaction."
                if comparison.worldline_compaction_retention_valid
                else "- Worldline failed to preserve timber compaction retention in this run."
            ),
            (
                "- Control C produces a plausible timber narrative, but it fails the causal-validity check after perturbation."
                if not comparison.control_post_perturbation_valid
                else "- Control C unexpectedly passed the timber causal-validity check in this run."
            ),
            (
                "- Contradiction gap: "
                f"Worldline={comparison.worldline_contradiction_count}, Control C={comparison.control_contradiction_count}."
            ),
        ]
    )


def _route_cut_summary(comparison: NegativeControlComparison) -> str:
    return "\n".join(
        [
            "### Route-Cut Reading",
            "",
            (
                "- Worldline retains route-cut / battlefield consequences with executable provenance through compaction."
                if comparison.worldline_compaction_retention_valid
                else "- Worldline failed to retain route-cut compaction provenance in this run."
            ),
            (
                "- Control C can tell a coherent corridor-disruption story, but it still lacks executable dependency edges and retained entity-specific provenance."
                if not comparison.control_compaction_retention_valid
                else "- Control C unexpectedly retained route-cut compaction validity in this run."
            ),
            (
                "- Contradiction gap: "
                f"Worldline={comparison.worldline_contradiction_count}, Control C={comparison.control_contradiction_count}."
            ),
        ]
    )


def _flag(value: bool) -> str:
    return "pass" if value else "fail"


if __name__ == "__main__":
    main()
