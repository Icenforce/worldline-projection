from pathlib import Path

from worldline.report_controls import DEFAULT_COMPARISON_SEEDS, main, render_comparison_report, write_comparison_report


def test_render_comparison_report_includes_seed_count_and_aggregate_metrics():
    report = render_comparison_report(seeds=DEFAULT_COMPARISON_SEEDS, size=64)

    assert "# Gate 5 Multi-Seed Comparison Report" in report
    assert "- seed count: `5`" in report
    assert "- seeds: `7, 11, 13, 17, 19`" in report
    assert "## Timber Perturbation: Worldline vs Control C" in report
    assert "## Route-Cut / Battlefield: Worldline vs Control C" in report
    assert "Post-perturbation pass rate" in report
    assert "Compaction retention pass rate" in report
    assert "Mean perturbation consequence rate" in report
    assert "Mean contradiction count" in report
    assert "Aggregate contradiction gap (Control C - Worldline)" in report
    assert "Worldline=5/5 (1.00), Control C=0/5 (0.00)" in report
    assert "mean=2.00, total=10" in report
    assert "mean=3.00, total=15" in report
    assert "## Limitations" in report


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
    assert "Aggregate contradiction gap (Control C - Worldline)" in contents
