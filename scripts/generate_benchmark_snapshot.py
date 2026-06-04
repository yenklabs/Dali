#!/usr/bin/env python3
"""Regenerate docs/assets/dali-v0.2-benchmark-snapshot.png for the README.

Data source: results/v0.2/README.md (2026-05-26 public benchmark run)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs" / "assets" / "dali-v0.2-benchmark-snapshot.png"

TITLE = "Dali v0.2 Evidence Reconstructability Benchmark"
SUBTITLE = (
    "Evaluating whether AI-generated legal citations remain attributable, "
    "verifiable, and reconstructable over time."
)
PATHWAY = "Generated citation -> Retrieved source -> Verified state -> Evidence artifact -> Reconstruction test"
FOOTER = "Source: results/v0.2/README.md - 2026-05-26 public benchmark run"

METRICS = [
    ("450", "prompt evaluations"),
    ("524", "citations evaluated"),
    ("5", "coverage tracks"),
    ("8", "prompt categories"),
]

JURISDICTION_ROWS = [
    ("UK / Commonwealth", 76, "#4ade80"),
    ("Policy / regulatory", 57, "#38bdf8"),
    ("US legal", 33, "#facc15"),
    ("Adversarial traps", 29, "#fb923c"),
    ("Brazil / Civil Law", 3, "#f87171"),
]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _rounded(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: str | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def main() -> None:
    width, height = 1600, 820
    image = Image.new("RGB", (width, height), "#101820")
    draw = ImageDraw.Draw(image)

    title_font = _font(54, bold=True)
    subtitle_font = _font(28)
    section_font = _font(30, bold=True)
    label_font = _font(23)
    label_bold = _font(25, bold=True)
    metric_font = _font(42, bold=True)
    small_font = _font(18)

    _rounded(draw, (48, 42, width - 48, height - 42), 28, "#0f1724", "#334155", 2)

    draw.text((90, 84), TITLE, font=title_font, fill="#f8fafc")
    draw.text((90, 154), SUBTITLE, font=subtitle_font, fill="#cbd5e1")

    chart_left = 330
    chart_top = 280
    chart_width = 1050
    label_left = 90
    row_gap = 68
    bar_height = 38

    draw.text((90, 230), "Verified citation URLs by coverage track", font=section_font, fill="#f8fafc")

    for pct in [0, 25, 50, 75, 100]:
        x = chart_left + int(chart_width * pct / 100)
        draw.line((x, chart_top - 40, x, chart_top + 325), fill="#233044", width=1)
        draw.text((x - 18, chart_top - 72), f"{pct}%", font=small_font, fill="#94a3b8")
    draw.line((chart_left, chart_top - 16, chart_left + chart_width, chart_top - 16), fill="#334155", width=2)

    for index, (label, pct, color) in enumerate(JURISDICTION_ROWS):
        y = chart_top + index * row_gap
        draw.text((label_left, y + 6), label, font=label_font, fill="#cbd5e1")
        bar_width = max(10, int(chart_width * pct / 100))
        _rounded(draw, (chart_left, y, chart_left + bar_width, y + bar_height), 9, color)
        draw.text((chart_left + bar_width + 18, y + 3), f"{pct}%", font=label_bold, fill="#f8fafc")

    card_width = 280
    card_height = 82
    card_gap = 26
    total_cards_width = 4 * card_width + 3 * card_gap
    card_x = (width - total_cards_width) // 2
    card_y = 650
    for index, (value, label) in enumerate(METRICS):
        x = card_x + index * (card_width + card_gap)
        _rounded(draw, (x, card_y, x + card_width, card_y + card_height), 16, "#172033", "#475569", 2)
        draw.text((x + 28, card_y + 18), value, font=metric_font, fill="#f8fafc")
        draw.text((x + 96, card_y + 29), label, font=small_font, fill="#cbd5e1")

    draw.text((90, 764), f"Evidence pathway: {PATHWAY}", font=small_font, fill="#cbd5e1")
    draw.text((90, 790), FOOTER, font=small_font, fill="#64748b")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
