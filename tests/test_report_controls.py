from pathlib import Path

from worldline.report_controls import DEFAULT_COMPARISON_SEEDS, main, render_comparison_report, write_comparison_report


def test_render_comparison_report_includes_seed_count_and_abc_metrics():
    report = render_comparison_report(seeds=DEFAULT_COMPARISON_SEEDS, size=64)

    assert "# Gate 5 Multi-Seed Comparison Report" in report
    assert "- seed count: `5`" in report
    assert "- seeds: `7, 11, 13, 17, 19`" in report
    assert "## Timber Perturbation: Worldline vs Controls A/B/C" in report
    assert "## Route-Cut / Battlefield: Worldline vs Controls A/B/C" in report
    assert "| Aggregate Metric | Worldline | Control A | Control B | Control C |" in report
    assert "Mean explanation depth" in report
    assert "Mean contradiction count" in report
    assert "Mean perturbation consequence rate" in report
    assert "Compaction explanation retention pass rate" in report
    assert "Control A: contradiction gap mean=" in report
    assert "Control B: contradiction gap mean=" in report
    assert "Control C: contradiction gap mean=" in report
    assert "Control A is intentionally random and uncoupled" in report
    assert "Control B is intentionally heuristic and spatially plausible" in report
    assert "Control C remains the strongest post-hoc explanation opponent" in report


def test_write_comparison_report_creates_markdown_file(tmp_path):
    output = tmp_path / "reports" / "multiseed_comparison.md"

    written = write_comparison_report(output, seeds=DEFAULT_COMPARISON_SEEDS, size=64)

    assert written == output
    assert output.exists()
    assert output.read_text(encoding="utf-8").startswith("# Gate 5 Multi-Seed Comparison Report\n")


def test_report_controls_main_writes_requested_output(tmp_path, capsys):
    output = tmp_path / "cli" / "comparison.md"

    main(["--output", str(output), "--seed", "7", "--seed", "11", "--seed", "13", "--seed", "17", "--seed", "19", "--size", "64"])

    captured = capsys.readouterr()
    assert Path(captured.out.strip()) == output
    assert output.exists()
    contents = output.read_text(encoding="utf-8")
    assert "seed count: `5`" in contents
    assert "Control A | Control B | Control C" in contents
