#!/usr/bin/env python3
"""Regenerate docs/assets/dali-v0.2-benchmark-snapshot.png for the README hero.

Requires: pip install matplotlib
Data source: results/v0.2/README.md (2026-05-26 public benchmark run)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs" / "assets" / "dali-v0.2-benchmark-snapshot.png"

TITLE = "Dali v0.2 Reproducibility & Attribution Benchmark"
SUBTITLE = (
    "Open evidentiary infrastructure for legal AI — not merely whether a citation exists, "
    "but whether the pathway can be attributed, verified, and reconstructed later."
)

PIPELINE_STAGES = [
    "Generated\nCitation",
    "Retrieved\nSource",
    "Verified\nState",
    "Evidence\nArtifact",
    "Reconstruction\nTest",
    "Pass /\nFail",
]

METRICS = [
    ("Policy-\nversioned", "reproducible runs", "same inputs → same scores"),
    ("524", "attribution probes", "citation + retrieval pathway"),
    ("Evidence\nhashes", "per evaluation", "deterministic artifacts"),
    ("76% → 3%", "durability gap", "UK verified vs Brazil (v0.2)"),
]

JURISDICTION_ROWS = [
    ("UK / Commonwealth", 76, "#22c55e"),
    ("Research / policy", 57, "#3b82f6"),
    ("US legal", 33, "#eab308"),
    ("Adversarial traps", 29, "#f97316"),
    ("Brazil (Portuguese)", 3, "#ef4444"),
]

FOOTER = "Source: results/v0.2/README.md · 2026-05-26 · Tier 2 synthetic run (450 prompts × 3 models)"


def _rounded_box(ax, x, y, w, h, text, *, face="#1e293b", edge="#475569", fontsize=9, bold=False):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.015,rounding_size=0.03",
        linewidth=1.2,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
        zorder=2,
    )
    ax.add_patch(patch)
    weight = "bold" if bold else "normal"
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color="#f8fafc",
        transform=ax.transAxes,
        zorder=3,
        linespacing=1.15,
    )


def _metric_card(ax, x, y, w, h, value, label, sub):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1,
        edgecolor="#334155",
        facecolor="#1e293b",
        transform=ax.transAxes,
        zorder=1,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.64, value, ha="center", va="center", fontsize=14, fontweight="bold", color="#f8fafc", transform=ax.transAxes, zorder=2, linespacing=1.1)
    ax.text(x + w / 2, y + h * 0.38, label, ha="center", va="center", fontsize=9, color="#cbd5e1", transform=ax.transAxes, zorder=2)
    ax.text(x + w / 2, y + h * 0.14, sub, ha="center", va="center", fontsize=7.5, color="#94a3b8", transform=ax.transAxes, zorder=2)


def _draw_pipeline(ax) -> None:
    ax.set_axis_off()
    ax.set_facecolor("#0f172a")
    ax.text(0.02, 0.92, "What Dali measures (evidence pathway)", ha="left", va="top", fontsize=12, fontweight="bold", color="#e2e8f0", transform=ax.transAxes)
    ax.text(
        0.02,
        0.78,
        "Each probe traces attribution and reconstructability — not only citation existence.",
        ha="left",
        va="top",
        fontsize=8.5,
        color="#94a3b8",
        transform=ax.transAxes,
    )

    n = len(PIPELINE_STAGES)
    box_w = 0.115
    gap = (0.96 - n * box_w) / (n - 1)
    y, h = 0.22, 0.48
    x0 = 0.02
    centers = []
    for i, stage in enumerate(PIPELINE_STAGES):
        x = x0 + i * (box_w + gap)
        edge = "#22c55e" if i == n - 1 else "#3b82f6"
        face = "#14532d" if i == n - 1 else "#1e3a5f"
        _rounded_box(ax, x, y, box_w, h, stage, face=face, edge=edge, fontsize=8.5, bold=(i == 0 or i == n - 1))
        centers.append((x + box_w / 2, y + h / 2))
        if i > 0:
            prev_x = x0 + (i - 1) * (box_w + gap) + box_w
            arrow = FancyArrowPatch(
                (prev_x, y + h / 2),
                (x, y + h / 2),
                transform=ax.transAxes,
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.5,
                color="#64748b",
                zorder=1,
            )
            ax.add_patch(arrow)


def main() -> None:
    fig = plt.figure(figsize=(16, 10), facecolor="#0f172a")
    fig.subplots_adjust(left=0.04, right=0.96, top=0.94, bottom=0.05)

    fig.text(0.5, 0.97, TITLE, ha="center", va="top", fontsize=21, fontweight="bold", color="#f8fafc")
    fig.text(0.5, 0.935, SUBTITLE, ha="center", va="top", fontsize=10, color="#94a3b8", wrap=True)

    ax_pipe = fig.add_axes([0.02, 0.72, 0.96, 0.18])
    _draw_pipeline(ax_pipe)

    ax_cards = fig.add_axes([0, 0.54, 1, 0.14])
    ax_cards.set_axis_off()
    ax_cards.set_facecolor("#0f172a")
    card_w, card_h, gap = 0.21, 0.88, 0.025
    start_x = (1 - (4 * card_w + 3 * gap)) / 2
    for i, (value, label, sub) in enumerate(METRICS):
        _metric_card(ax_cards, start_x + i * (card_w + gap), 0.04, card_w, card_h, value, label, sub)

    ax = fig.add_axes([0.18, 0.08, 0.78, 0.42])
    ax.set_facecolor("#0f172a")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(JURISDICTION_ROWS) + 1)
    ax.invert_yaxis()
    ax.set_title(
        "Verification durability by jurisdiction (v0.2)\n"
        "HTTP recoverability under fixed policy version — durability gap across jurisdictions",
        loc="left",
        fontsize=11,
        fontweight="bold",
        color="#e2e8f0",
        pad=14,
    )
    ax.tick_params(colors="#94a3b8", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#334155")
    ax.spines["bottom"].set_color("#334155")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="x", color="#1e293b", linestyle="-", linewidth=0.8)
    ax.set_axisbelow(True)

    y_pos = [i + 0.65 for i in range(len(JURISDICTION_ROWS))]
    labels = [row[0] for row in JURISDICTION_ROWS]
    pcts = [row[1] for row in JURISDICTION_ROWS]
    colors = [row[2] for row in JURISDICTION_ROWS]
    ax.barh(y_pos, pcts, height=0.55, color=colors, alpha=0.92, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="#e2e8f0", fontsize=10)
    for y, pct in zip(y_pos, pcts):
        ax.text(pct + 1.5, y, f"{pct}%", ha="left", va="center", fontsize=10, fontweight="bold", color="#f8fafc")

    fig.text(0.04, 0.02, FOOTER, ha="left", va="bottom", fontsize=8, color="#64748b")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
