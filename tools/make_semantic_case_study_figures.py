"""Create report figures directly from the sealed S0 semantic run artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.provenance import sha256_file, validate_run_manifest


COLORS = {
    "navy": "#244A73",
    "blue": "#5B8DB8",
    "teal": "#4C9A8A",
    "amber": "#D79A3B",
    "slate": "#6B7280",
}


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "axes.titleweight": "bold",
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def _save(fig: plt.Figure, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def detector_figure(metrics: dict, output_dir: Path, table_dir: Path) -> None:
    test = metrics["test"]
    rows = [
        {"metric": "Average Precision", "value": test["auc_pr"], "split": "test"},
        {"metric": "Precision", "value": test["precision"], "split": "test"},
        {"metric": "Recall", "value": test["recall"], "split": "test"},
        {"metric": "F1", "value": test["f1"], "split": "test"},
    ]
    _write_csv(table_dir / "semantic_detector_metrics.csv", rows)

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labels = [row["metric"] for row in rows]
    values = [float(row["value"]) for row in rows]
    bars = ax.bar(
        labels,
        values,
        color=[COLORS["navy"], COLORS["blue"], COLORS["amber"], COLORS["teal"]],
        width=0.62,
    )
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("S0 semantic case-study detector performance")
    ax.grid(axis="y", color="#D8DEE6", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.025,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )
    ax.text(
        0.0,
        -0.23,
        "Chronological test split: n = 7,500, frauds = 45. Threshold frozen on validation data.",
        transform=ax.transAxes,
        fontsize=7.2,
        color="#4B5563",
    )
    fig.subplots_adjust(bottom=0.25)
    _save(fig, output_dir / "semantic_detector_metrics")


def assurance_figure(summary: dict, calibration: dict, output_dir: Path, table_dir: Path) -> None:
    delivered = summary["rows"] - summary["fallbacks"]
    rows = [
        {
            "measure": "Guarded LLM accepted",
            "successes": delivered,
            "n": summary["rows"],
            "rate": delivered / summary["rows"],
        },
        {
            "measure": "Deterministic fallback",
            "successes": summary["fallbacks"],
            "n": summary["rows"],
            "rate": summary["fallback_rate_wilson"]["rate"],
        },
        {
            "measure": "Transport failure",
            "successes": summary["transport_failures"],
            "n": summary["rows"],
            "rate": summary["transport_failure_rate"]["rate"],
        },
        {
            "measure": "Calibration attacks intercepted",
            "successes": int(calibration["attack_interception"]["rate"] * calibration["attack_interception"]["n"]),
            "n": calibration["attack_interception"]["n"],
            "rate": calibration["attack_interception"]["rate"],
        },
        {
            "measure": "Faithful controls accepted",
            "successes": int(calibration["control_acceptance"]["rate"] * calibration["control_acceptance"]["n"]),
            "n": calibration["control_acceptance"]["n"],
            "rate": calibration["control_acceptance"]["rate"],
        },
    ]
    _write_csv(table_dir / "semantic_explanation_assurance.csv", rows)

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels = [
        "LLM\naccepted",
        "Fallback",
        "Transport\nfailure",
        "Attacks\nintercepted",
        "Controls\naccepted",
    ]
    values = [float(row["rate"]) for row in rows]
    bars = ax.bar(
        labels,
        values,
        color=[COLORS["teal"], COLORS["amber"], COLORS["slate"], COLORS["navy"], COLORS["blue"]],
        width=0.64,
    )
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Rate")
    ax.set_title("S0 structured-explanation delivery and validator calibration")
    ax.grid(axis="y", color="#D8DEE6", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    for bar, row in zip(bars, rows):
        rate = float(row["rate"])
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 0.025,
            f"{rate:.0%}\n{row['successes']}/{row['n']}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            fontweight="bold",
        )
    ax.text(
        0.0,
        -0.24,
        "Delivery results use 25 frozen test alerts. Calibration uses 150 attacks and 40 faithful controls.",
        transform=ax.transAxes,
        fontsize=7.2,
        color="#4B5563",
    )
    fig.subplots_adjust(bottom=0.25)
    _save(fig, output_dir / "semantic_explanation_assurance")


def brief_comparison_table(rows: list[dict], table_dir: Path) -> None:
    accepted = [row for row in rows if not row.get("fallback", False)]
    deterministic = [str(row["deterministic_brief"]) for row in accepted]
    delivered = [str(row["delivered_brief"]) for row in accepted]

    def mean(values: list[int]) -> float:
        return sum(values) / len(values) if values else 0.0

    deterministic_named = []
    delivered_named = []
    for row, deterministic_text, delivered_text in zip(accepted, deterministic, delivered):
        labels = [
            str(item["display_label"])
            for item in row["minimized_llm_payload"]["evidence"]
        ]
        deterministic_named.append(sum(label in deterministic_text for label in labels))
        delivered_named.append(sum(label in delivered_text for label in labels))

    _write_csv(
        table_dir / "semantic_brief_comparison.csv",
        [
            {"measure": "Accepted guarded LLM briefs", "value": len(accepted)},
            {"measure": "Unique analyst-visible LLM brief strings", "value": len(set(delivered))},
            {"measure": "Deterministic mean words", "value": mean([len(text.split()) for text in deterministic])},
            {"measure": "Guarded LLM mean words", "value": mean([len(text.split()) for text in delivered])},
            {"measure": "Deterministic mean characters", "value": mean([len(text) for text in deterministic])},
            {"measure": "Guarded LLM mean characters", "value": mean([len(text) for text in delivered])},
            {"measure": "Deterministic mean named evidence items", "value": mean(deterministic_named)},
            {"measure": "Guarded LLM mean named evidence items", "value": mean(delivered_named)},
        ],
    )


def _row_count(path: Path) -> int:
    with path.open(newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def write_results_manifest(run_dir: Path, output_dir: Path, table_dir: Path, path: Path) -> None:
    run_manifest = run_dir / "run_manifest.json"
    outputs = [
        table_dir / "semantic_detector_metrics.csv",
        table_dir / "semantic_explanation_assurance.csv",
        table_dir / "semantic_brief_comparison.csv",
        output_dir / "semantic_detector_metrics.png",
        output_dir / "semantic_detector_metrics.svg",
        output_dir / "semantic_detector_metrics.pdf",
        output_dir / "semantic_detector_metrics.tiff",
        output_dir / "semantic_explanation_assurance.png",
        output_dir / "semantic_explanation_assurance.svg",
        output_dir / "semantic_explanation_assurance.pdf",
        output_dir / "semantic_explanation_assurance.tiff",
    ]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_run": {
            "run_id": run_dir.name,
            "manifest_sha256": sha256_file(run_manifest),
        },
        "inputs": {
            relative: {"sha256": sha256_file(run_dir / relative)}
            for relative in (
                "metrics.json",
                "explanation_summary.json",
                "semantic_validator_calibration.json",
                "explanation_comparison.jsonl",
            )
        },
        "outputs": {
            output.as_posix(): {
                "sha256": sha256_file(output),
                **({"rows": _row_count(output)} if output.suffix == ".csv" else {}),
            }
            for output in outputs
        },
        "source_code_sha256": {
            "tools/make_semantic_case_study_figures.py": sha256_file(Path(__file__)),
            "src/provenance.py": sha256_file(ROOT / "src/provenance.py"),
        },
        "interpretation_boundary": (
            "S0 is a separate single-seed synthetic operational case study and is not "
            "directly comparable with the ULB G0-G7 benchmark."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="experiments/runs/2026-07-26_s0_seed42")
    parser.add_argument("--output-dir", default="reports/figures")
    parser.add_argument("--table-dir", default="reports/tables")
    parser.add_argument("--manifest", default="reports/semantic_results_manifest.json")
    args = parser.parse_args()

    run_dir = Path(args.run)
    validate_run_manifest(run_dir, expected_group="s0")
    metrics = json.loads((run_dir / "metrics.json").read_text())
    summary = json.loads((run_dir / "explanation_summary.json").read_text())
    calibration = json.loads((run_dir / "semantic_validator_calibration.json").read_text())
    comparisons = [
        json.loads(line)
        for line in (run_dir / "explanation_comparison.jsonl").read_text().splitlines()
        if line.strip()
    ]
    _style()
    detector_figure(metrics, Path(args.output_dir), Path(args.table_dir))
    assurance_figure(summary, calibration, Path(args.output_dir), Path(args.table_dir))
    brief_comparison_table(comparisons, Path(args.table_dir))
    write_results_manifest(
        run_dir,
        Path(args.output_dir),
        Path(args.table_dir),
        Path(args.manifest),
    )
    print("semantic case-study figures and source tables written")


if __name__ == "__main__":
    main()
