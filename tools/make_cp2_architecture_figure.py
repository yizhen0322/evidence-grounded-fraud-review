"""Generate Figure 3.1 as a restrained academic methodology schematic.

Core conclusion
---------------
The study produces one manifest-linked immutable record under experimental
control. The local LLM is a bounded candidate stage inside that record, not a
second detector: its raw output is retained and is either accepted or replaced
by deterministic fallback, never repaired. The analyst workbench sits below a
one-way evidence boundary, reads the record, and writes nothing into it.

Figure contract
---------------
Archetype: ruled two-column ledger. A single vertical provenance spine carries
the four-stage chain; a single heavy horizontal rule is the evidence boundary;
the right-hand column answers one repeated question, "what is written?".
Backend: Python/matplotlib only.
Final size: 154 mm report text width by 108 mm.
Exports: editable SVG/PDF, 600 dpi TIFF, and 300 dpi PNG.

All drawing coordinates are millimetres. The axes fill the figure exactly and
the limits match the figure size, so one data unit is one millimetre and every
value below is directly measurable in the exported artwork. Do not introduce
bbox_inches="tight"; it would silently break the 154 mm width guarantee.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures" / "cp2_system_architecture"
MEETING_COPIES = (
    ROOT
    / "supervisor_meeting"
    / "progress_B_working_draft"
    / "report"
    / "evidence"
    / "01_system_architecture.png",
    ROOT
    / "supervisor_meeting"
    / "meeting_01"
    / "evidence"
    / "01_system_architecture.png",
)

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7.0,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)

# Five tones, separated in grayscale at roughly 10 / 21 / 37 / 57 / 100 percent.
INK = "#1A1A1A"
ACCENT = "#1F3B57"
MID = "#5A5F63"
RULE = "#8C9298"
WHITE = "#FFFFFF"

FIG_W = 154.0
FIG_H = 108.0

X_RULE_L = 10.0
X_RULE_R = 144.0
X_AXIS_LABEL = 15.5
X_SPINE = 24.0
X_TEXT = 30.5

Y_HEADING = 101.0
Y_TOP_RULE = 99.2
Y_SPINE_TOP = 96.0
Y_SPINE_END = 42.8
Y_ARROW_TIP = 36.2
Y_READ_LABEL = 39.0
Y_BOUNDARY_LABEL = 36.0
Y_BOUNDARY = 34.8
Y_PLANE_LABEL = 30.9
Y_DASH_TOP = 28.3
Y_BOTTOM_RULE = 7.0

NOTE_GAP = 4.0
NOTE_LEAD = 3.4
MARKER_SIDE = 2.0

SIZE_HEADING = 7.0
SIZE_TITLE = 7.8
SIZE_NOTE = 7.0
SIZE_RECORD = 6.6
SIZE_CROSSING = 6.8
SIZE_AXIS_LABEL = 6.4


@dataclass(frozen=True)
class Row:
    """One ledger row: a marker on the spine, a title block, and a record entry."""

    y: float
    title: str
    notes: tuple[str, ...]
    record: str
    solid: bool
    accented: bool


# Stage wording is deliberately terse. The report caption carries the detail;
# the figure carries the relationships.
CHAIN: tuple[Row, ...] = (
    Row(
        y=93.6,
        title="Leakage-controlled detector experiments",
        notes=("Fixed splits, training-only fitting, five seeds",),
        record="Predictions, splits, and metrics",
        solid=True,
        accented=True,
    ),
    Row(
        y=81.6,
        title="Frozen detector and signed SHAP evidence",
        notes=("Validation-selected threshold applied unchanged",),
        record="Threshold, SHAP, reason codes",
        solid=True,
        accented=True,
    ),
    # The one hollow marker above the boundary: a provisional candidate, not a
    # second detector.
    Row(
        y=69.6,
        title="Local LLM narrative candidate",
        notes=(
            "Minimised reason-code package over loopback",
            "No raw rows, exact values, scores, or labels",
        ),
        record="Raw candidate text, kept unmodified",
        solid=False,
        accented=True,
    ),
    Row(
        y=54.2,
        title="Deterministic validation and delivery",
        notes=(
            "Format, completeness, grounding, direction",
            "Accepted or replaced by fallback, never repaired",
        ),
        record="Validation outcome; delivered brief",
        solid=True,
        accented=True,
    ),
)

OPERATIONAL: tuple[Row, ...] = (
    Row(
        y=27.0,
        title="Analyst workbench (React, FastAPI)",
        notes=("Loads manifested artifact paths only",),
        record="Nothing — read-only consumer",
        solid=False,
        accented=False,
    ),
    Row(
        y=17.2,
        title="Analyst workflow store (SQLite)",
        notes=(
            "Status, routing decision, note, revision",
            "Analyst routes the alert; no automated verdict",
        ),
        record="Workflow metadata, separate plane",
        solid=False,
        accented=False,
    ),
)


def rule(ax, y: float, *, color: str, linewidth: float) -> None:
    ax.plot(
        [X_RULE_L, X_RULE_R],
        [y, y],
        color=color,
        linewidth=linewidth,
        solid_capstyle="butt",
        zorder=1,
    )


def marker(ax, y: float, *, solid: bool, color: str) -> None:
    half = MARKER_SIDE / 2.0
    ax.add_patch(
        Rectangle(
            (X_SPINE - half, y - half),
            MARKER_SIDE,
            MARKER_SIDE,
            facecolor=color if solid else WHITE,
            edgecolor=color,
            linewidth=0.9,
            zorder=4,
        )
    )


def draw_row(ax, row: Row) -> None:
    marker(ax, row.y, solid=row.solid, color=ACCENT if row.accented else MID)
    ax.text(
        X_TEXT,
        row.y,
        row.title,
        fontsize=SIZE_TITLE,
        fontweight="bold",
        color=INK,
        ha="left",
        va="center",
        zorder=5,
    )
    for index, note in enumerate(row.notes):
        ax.text(
            X_TEXT,
            row.y - NOTE_GAP - index * NOTE_LEAD,
            note,
            fontsize=SIZE_NOTE,
            color=MID,
            ha="left",
            va="center",
            zorder=5,
        )
    # The right-hand column answers one repeated question and needs no
    # connector: shared baselines carry the relation.
    ax.text(
        X_RULE_R,
        row.y,
        row.record,
        fontsize=SIZE_RECORD,
        color=INK if row.record.startswith("Nothing") else MID,
        ha="right",
        va="center",
        zorder=5,
    )


def draw_frame(ax) -> None:
    ax.text(
        X_RULE_L,
        Y_HEADING,
        "RESEARCH EVIDENCE PLANE",
        fontsize=SIZE_HEADING,
        fontweight="bold",
        color=INK,
        ha="left",
        va="baseline",
        zorder=5,
    )
    ax.text(
        X_RULE_R,
        Y_HEADING,
        "WHAT IS WRITTEN",
        fontsize=SIZE_HEADING,
        fontweight="bold",
        color=INK,
        ha="right",
        va="baseline",
        zorder=5,
    )
    rule(ax, Y_TOP_RULE, color=RULE, linewidth=0.7)
    rule(ax, Y_BOTTOM_RULE, color=RULE, linewidth=0.7)


def draw_chain(ax) -> None:
    # The spine is the provenance record itself, not a flowchart connector.
    ax.plot(
        [X_SPINE, X_SPINE],
        [Y_SPINE_TOP, Y_SPINE_END],
        color=ACCENT,
        linewidth=1.2,
        solid_capstyle="butt",
        zorder=2,
    )
    ax.text(
        X_AXIS_LABEL,
        (Y_SPINE_TOP + Y_SPINE_END) / 2.0,
        "MANIFEST-LINKED IMMUTABLE RECORD",
        fontsize=SIZE_AXIS_LABEL,
        color=MID,
        ha="center",
        va="center",
        rotation=90,
        rotation_mode="anchor",
        zorder=5,
    )
    for row in CHAIN:
        draw_row(ax, row)


def draw_boundary(ax) -> None:
    # The only arrowhead in the figure. One crossing, downward, read-only.
    ax.add_patch(
        FancyArrowPatch(
            (X_SPINE, Y_SPINE_END),
            (X_SPINE, Y_ARROW_TIP),
            arrowstyle="-|>",
            mutation_scale=8.0,
            linewidth=1.2,
            color=ACCENT,
            shrinkA=0.0,
            shrinkB=0.0,
            zorder=3,
        )
    )
    ax.text(
        X_SPINE + 3.0,
        Y_READ_LABEL,
        "read only",
        fontsize=SIZE_CROSSING,
        color=ACCENT,
        ha="left",
        va="center",
        zorder=5,
    )
    ax.text(
        X_RULE_R,
        Y_BOUNDARY_LABEL,
        "EVIDENCE BOUNDARY",
        fontsize=SIZE_HEADING,
        fontweight="bold",
        color=INK,
        ha="right",
        va="baseline",
        zorder=5,
    )
    rule(ax, Y_BOUNDARY, color=INK, linewidth=1.9)


def draw_operational(ax) -> None:
    ax.text(
        X_RULE_L,
        Y_PLANE_LABEL,
        "OPERATIONAL PLANE",
        fontsize=SIZE_HEADING,
        fontweight="bold",
        color=INK,
        ha="left",
        va="baseline",
        zorder=5,
    )
    # Dashed, grey, and detached from the boundary rule: the provenance chain
    # does not continue into the analyst's workspace.
    ax.plot(
        [X_SPINE, X_SPINE],
        [Y_DASH_TOP, OPERATIONAL[-1].y],
        color=MID,
        linewidth=0.85,
        linestyle=(0, (2.4, 1.8)),
        solid_capstyle="butt",
        zorder=2,
    )
    for row in OPERATIONAL:
        draw_row(ax, row)


def main() -> None:
    fig = plt.figure(figsize=(FIG_W / 25.4, FIG_H / 25.4), facecolor=WHITE)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, FIG_W)
    ax.set_ylim(0.0, FIG_H)
    ax.axis("off")

    draw_frame(ax)
    draw_chain(ax)
    draw_boundary(ax)
    draw_operational(ax)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT.with_suffix(".svg"), facecolor=WHITE)
    fig.savefig(OUT.with_suffix(".pdf"), facecolor=WHITE)
    fig.savefig(
        OUT.with_suffix(".tiff"),
        dpi=600,
        facecolor=WHITE,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    fig.savefig(OUT.with_suffix(".png"), dpi=300, facecolor=WHITE)
    plt.close(fig)

    for destination in MEETING_COPIES:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT.with_suffix(".png"), destination)

    print(OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
