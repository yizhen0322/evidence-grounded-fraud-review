"""Generate submission-ready bar charts for the CP2 report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_CSV = REPO_ROOT / "reports" / "tables" / "results_summary.csv"
FAITHFULNESS_JSON = (
    REPO_ROOT
    / "experiments"
    / "runs"
    / "2026-07-14_g5_seed42"
    / "faithfulness.json"
)
OUTPUT_DIR = REPO_ROOT / "reports" / "figures"

GROUP_ORDER = ["g0", "g1", "g2", "g3", "g6", "g7"]
GROUP_LABELS = ["G0", "G1", "G2", "G3", "G6", "G7"]

INK = "#252A34"
BLUE = "#356A9A"
BLUE_LIGHT = "#8FB3D3"
ORANGE = "#C9793D"
TEAL = "#2C7A78"
GRID = "#D8DCE2"
NEUTRAL = "#7C8798"


def _apply_style() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "Arial",
        "DejaVu Sans",
        "Liberation Sans",
    ]
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["font.size"] = 8
    plt.rcParams["axes.labelsize"] = 8
    plt.rcParams["xtick.labelsize"] = 7
    plt.rcParams["ytick.labelsize"] = 7
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["legend.frameon"] = False


def _finish_axis(axis: plt.Axes) -> None:
    axis.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(length=3, width=0.7, color=INK)
    axis.spines["left"].set_color(INK)
    axis.spines["bottom"].set_color(INK)


def _panel_label(axis: plt.Axes, label: str) -> None:
    axis.text(
        -0.13,
        1.05,
        label,
        transform=axis.transAxes,
        fontsize=9,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=INK,
    )


def _annotate_bars(
    axis: plt.Axes,
    bars,
    *,
    decimals: int = 3,
    offset: float = 0.01,
    upper_errors: np.ndarray | None = None,
) -> None:
    if upper_errors is None:
        upper_errors = np.zeros(len(bars))
    for bar, error in zip(bars, upper_errors, strict=True):
        value = float(bar.get_height())
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + float(error) + offset,
            f"{value:.{decimals}f}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=INK,
        )


def _export(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(
        OUTPUT_DIR / f"{stem}.tiff",
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def make_detector_figure() -> None:
    frame = pd.read_csv(RESULTS_CSV).set_index("group").loc[GROUP_ORDER]
    x = np.arange(len(GROUP_ORDER))

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8), constrained_layout=True)

    f1 = frame["test_f1_mean"].to_numpy()
    f1_std = frame["test_f1_std"].to_numpy()
    f1_colors = [BLUE_LIGHT] * len(GROUP_ORDER)
    f1_colors[GROUP_ORDER.index("g6")] = TEAL
    bars = axes[0].bar(
        x,
        f1,
        yerr=f1_std,
        capsize=3,
        width=0.68,
        color=f1_colors,
        edgecolor=INK,
        linewidth=0.6,
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
    )
    axes[0].set_xticks(x, GROUP_LABELS)
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("Test F1")
    _annotate_bars(
        axes[0],
        bars,
        decimals=3,
        offset=0.018,
        upper_errors=f1_std,
    )
    _finish_axis(axes[0])
    _panel_label(axes[0], "a")

    width = 0.35
    precision = frame["test_precision_mean"].to_numpy()
    recall = frame["test_recall_mean"].to_numpy()
    p_bars = axes[1].bar(
        x - width / 2,
        precision,
        width,
        color=BLUE,
        edgecolor=INK,
        linewidth=0.5,
        label="Precision",
    )
    r_bars = axes[1].bar(
        x + width / 2,
        recall,
        width,
        color=ORANGE,
        edgecolor=INK,
        linewidth=0.5,
        label="Recall",
    )
    axes[1].set_xticks(x, GROUP_LABELS)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("Mean test score")
    axes[1].legend(loc="lower left", ncols=2, fontsize=6.5)
    _annotate_bars(axes[1], p_bars, decimals=2, offset=0.012)
    _annotate_bars(axes[1], r_bars, decimals=2, offset=0.012)
    _finish_axis(axes[1])
    _panel_label(axes[1], "b")

    false_positive = frame["test_fp_mean"].to_numpy()
    false_negative = frame["test_fn_mean"].to_numpy()
    fp_std = frame["test_fp_std"].to_numpy()
    fn_std = frame["test_fn_std"].to_numpy()
    fp_bars = axes[2].bar(
        x - width / 2,
        false_positive,
        width,
        yerr=fp_std,
        capsize=2.5,
        color=BLUE,
        edgecolor=INK,
        linewidth=0.5,
        error_kw={"elinewidth": 0.7, "capthick": 0.7},
        label="False positive",
    )
    fn_bars = axes[2].bar(
        x + width / 2,
        false_negative,
        width,
        yerr=fn_std,
        capsize=2.5,
        color=ORANGE,
        edgecolor=INK,
        linewidth=0.5,
        error_kw={"elinewidth": 0.7, "capthick": 0.7},
        label="False negative",
    )
    axes[2].set_xticks(x, GROUP_LABELS)
    axes[2].set_ylim(0, 26)
    axes[2].set_ylabel("Mean test count")
    axes[2].legend(loc="upper left", fontsize=6.5)
    _annotate_bars(axes[2], fp_bars, decimals=1, offset=0.45)
    _annotate_bars(axes[2], fn_bars, decimals=1, offset=0.45)
    _finish_axis(axes[2])
    _panel_label(axes[2], "c")

    _export(fig, "detector_metric_bars")


def _rate_and_ci(block: dict) -> tuple[float, float, float]:
    rate = float(block["rate"])
    low, high = (float(value) for value in block["ci95"])
    return rate, rate - low, high - rate


def make_narrative_figure() -> None:
    payload = json.loads(FAITHFULNESS_JSON.read_text())
    categories = ["Detected any\nviolation", "Fallback\ndelivery", "Accepted LLM\nnarrative"]
    arms = ["strict", "simple"]
    colors = [BLUE, ORANGE]
    x = np.arange(len(categories))
    width = 0.34

    fig, axis = plt.subplots(figsize=(5.4, 3.35), constrained_layout=True)

    for index, (arm, color) in enumerate(zip(arms, colors, strict=True)):
        record = payload["arms"][arm]
        violation = _rate_and_ci(
            record["off_policy_prevalence"]["detected_any_violation"]
        )
        fallback = _rate_and_ci(record["on_policy_delivery"]["fallback"])
        fallback_rate = fallback[0]
        fallback_low = fallback_rate - fallback[1]
        fallback_high = fallback_rate + fallback[2]
        accepted = (
            1.0 - fallback_rate,
            (1.0 - fallback_rate) - (1.0 - fallback_high),
            (1.0 - fallback_low) - (1.0 - fallback_rate),
        )
        values = np.array([violation[0], fallback[0], accepted[0]]) * 100
        lower = np.array([violation[1], fallback[1], accepted[1]]) * 100
        upper = np.array([violation[2], fallback[2], accepted[2]]) * 100
        positions = x + (index - 0.5) * width
        bars = axis.bar(
            positions,
            values,
            width,
            yerr=np.vstack([lower, upper]),
            capsize=3,
            color=color,
            edgecolor=INK,
            linewidth=0.6,
            error_kw={"elinewidth": 0.8, "capthick": 0.8},
            label=arm.capitalize() + " prompt",
        )
        for bar, value, upper_error in zip(bars, values, upper, strict=True):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                min(max(value + upper_error + 2.5, 5.5), 107.0),
                f"{value:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7,
                color=INK,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6},
            )

    axis.set_xticks(x, categories)
    axis.set_ylim(0, 110)
    axis.set_ylabel("Cases (%)")
    axis.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncols=2,
        fontsize=7,
    )
    _finish_axis(axis)
    _export(fig, "narrative_delivery_bars")


def main() -> None:
    _apply_style()
    make_detector_figure()
    make_narrative_figure()


if __name__ == "__main__":
    main()
