from pathlib import Path

from worldline.report_controls import main, render_comparison_report, write_comparison_report


def test_render_comparison_report_includes_required_sections_and_metrics():
    report = render_comparison_report(seed=12345, size=128)

    assert "# Gate 5 Formal Comparison Report" in report
    assert "## Timber Perturbation: Worldline vs Control C" in report
    assert "## Route-Cut / Battlefield: Worldline vs Control C" in report
    assert "Compaction retention validity" in report
    assert "Perturbation consequence rate" in report
    assert "Contradiction count" in report
    assert "Explanation depth" in report
    assert "## Limitations" in report
    assert "Worldline preserves a perturbation-linked timber explanation through compaction." in report
    assert "Perturbation consequence rate: Worldline=1.00, Control C=1.00." in report
    assert "Control C can tell a coherent corridor-disruption story" in report


def test_write_comparison_report_creates_markdown_file(tmp_path):
    output = tmp_path / "reports" / "latest_comparison.md"

    written = write_comparison_report(output, seed=12345, size=128)

    assert written == output
    assert output.exists()
    assert output.read_text(encoding="utf-8").startswith("# Gate 5 Formal Comparison Report\n")


def test_report_controls_main_writes_requested_output(tmp_path, capsys):
    output = tmp_path / "cli" / "comparison.md"

    main(["--output", str(output), "--seed", "12345", "--size", "128"])

    captured = capsys.readouterr()
    assert Path(captured.out.strip()) == output
    assert output.exists()
    contents = output.read_text(encoding="utf-8")
    assert "Worldline vs Control C" in contents
    assert "Post-perturbation causal validity" in contents
