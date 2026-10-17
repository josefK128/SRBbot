from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from create_current_performance_report import REGIMES, analyze, pct, tao


NAVY = colors.HexColor("#18324A")
BLUE = colors.HexColor("#2D6F9F")
ORANGE = colors.HexColor("#D07A28")
GRAY = colors.HexColor("#5D6873")
GRID = colors.HexColor("#D4DCE3")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF3DF")
BODY = colors.HexColor("#263440")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5))
styles.add(ParagraphStyle(name="SubtitleX", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=GRAY, spaceAfter=12))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=6, spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontSize=9, leading=12.5, textColor=BODY, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=7.3, leading=9.4, textColor=GRAY))
styles.add(ParagraphStyle(name="HeaderX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=9.4, textColor=colors.white))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontSize=9.2, leading=13, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=.7, borderPadding=8, spaceAfter=9))
styles.add(ParagraphStyle(name="CautionX", parent=styles["BodyText"], fontSize=8.8, leading=12.5, textColor=NAVY, backColor=PALE_AMBER, borderColor=ORANGE, borderWidth=.7, borderPadding=8, spaceBefore=5, spaceAfter=9))


def p(text, style="BodyX"):
    return Paragraph(str(text), styles[style])


def table(rows, widths, aligns=None):
    cooked = []
    for ri, row in enumerate(rows):
        cooked.append([p(value, "HeaderX" if ri == 0 else "SmallX") for value in row])
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), .45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if aligns:
        for index, align in enumerate(aligns):
            commands.append(("ALIGN", (index, 1), (index, -1), align))
    return Table(cooked, colWidths=widths, repeatRows=1, style=TableStyle(commands))


def regime_chart(result):
    drawing = Drawing(505, 185)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 52, 35, 420, 118
    chart.data = [
        [float(result["score"]["regimes"][code]["linked"] or 0) for code, _ in REGIMES],
        [float(result["breakout"]["regimes"][code]["linked"] or 0) for code, _ in REGIMES],
    ]
    chart.categoryAxis.categoryNames = [name for _, name in REGIMES]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.1f%%"
    chart.valueAxis.gridStrokeColor = GRID
    chart.bars[0].fillColor = BLUE
    chart.bars[1].fillColor = ORANGE
    chart.barSpacing = 2
    chart.groupSpacing = 12
    drawing.add(chart)
    drawing.add(String(158, 169, "Linked return by ±1% Tao condition", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    drawing.add(String(52, 160, "Score", fontSize=7, fillColor=BLUE))
    drawing.add(String(98, 160, "Breakout", fontSize=7, fillColor=ORANGE))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(.7 * inch, .55 * inch, 7.8 * inch, .55 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(.7 * inch, .36 * inch, "SRBbot brief performance report - ±1% Tao conditions")
    canvas.drawRightString(7.8 * inch, .36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(db_path: Path, output: Path):
    meta, result = analyze(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.fromisoformat(meta["start"]).strftime("%b %d, %Y %H:%M UTC")
    end = datetime.fromisoformat(meta["end"]).strftime("%b %d, %Y %H:%M UTC")
    leader = "Score" if result["score"]["ending_nav"] > result["breakout"]["ending_nav"] else "Breakout"
    gap = abs(result["score"]["ending_nav"] - result["breakout"]["ending_nav"])
    total_directional = meta["regime_counts"][-1] + meta["regime_counts"][1]
    story = [
        p("SRBbot brief performance update", "TitleX"),
        p(f"Score vs. Breakout under the new ±1% Tao market conditions | Cutoff: {end}", "SubtitleX"),
        p(f"<b>Headline:</b> {leader} leads by {gap:.4f} TAO. Breakout ends at {result['breakout']['ending_nav']:.4f} TAO ({pct(result['breakout']['return'])}); Score ends at {result['score']['ending_nav']:.4f} TAO ({pct(result['score']['return'])}). Reclassifying Tao conditions does not change trades or performance - only the regime attribution.", "CalloutX"),
        p("1 | Coverage and overall result", "H1X"),
        table([
            ["Window", "Samples", "Intervals", "Tao price change"],
            [f"{start} to {end}", meta["count"], meta["intervals"], pct(meta["tao_return"], 2)],
        ], [3.45*inch, .72*inch, .75*inch, 1.25*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 7),
        table([
            ["Metric", "Score", "Breakout"],
            ["Ending liquidation NAV", tao(result["score"]["ending_nav"]), tao(result["breakout"]["ending_nav"])],
            ["Net return", pct(result["score"]["return"]), pct(result["breakout"]["return"])],
            ["Maximum drawdown", pct(result["score"]["max_drawdown"]), pct(result["breakout"]["max_drawdown"])],
            ["Stake replacements", result["score"]["replacements"], result["breakout"]["replacements"]],
            ["Executed turnover", tao(result["score"]["turnover"], 2), tao(result["breakout"]["turnover"], 2)],
            ["Realized modeled costs", tao(result["score"]["costs"]), tao(result["breakout"]["costs"])],
        ], [2.8*inch, 1.65*inch, 1.65*inch], ["LEFT", "RIGHT", "RIGHT"]),
        p("2 | New Tao-condition distribution", "H1X"),
        table([
            ["Condition", "Definition", "Intervals", "Share"],
            ["Falling", "Tao move < -1%", meta["regime_counts"][-1], pct(meta["regime_counts"][-1] / meta["intervals"] * 100, 1)],
            ["Static", "Tao move within [-1%, +1%]", meta["regime_counts"][0], pct(meta["regime_counts"][0] / meta["intervals"] * 100, 1)],
            ["Rising", "Tao move > +1%", meta["regime_counts"][1], pct(meta["regime_counts"][1] / meta["intervals"] * 100, 1)],
        ], [1.1*inch, 2.7*inch, 1.0*inch, 1.0*inch], ["LEFT", "LEFT", "RIGHT", "RIGHT"]),
        p(f"The ±1% definition identifies {total_directional} directional intervals instead of 4 under ±2%, providing a materially stronger basis for conditional comparison.", "CautionX"),
        p("3 | Strategy performance by condition", "H1X"),
    ]
    rows = [["Condition", "n", "Score linked", "Score P/L", "Breakout linked", "Breakout P/L"]]
    for code, name in REGIMES:
        s = result["score"]["regimes"][code]
        b = result["breakout"]["regimes"][code]
        rows.append([name, s["n"], pct(s["linked"]), tao(s["delta_tao"]), pct(b["linked"]), tao(b["delta_tao"])])
    story += [
        table(rows, [1.0*inch, .38*inch, 1.05*inch, 1.05*inch, 1.18*inch, 1.12*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 6),
        regime_chart(result),
        p("4 | Brief interpretation", "H1X"),
        p(f"<b>Static:</b> Breakout produced {pct(result['breakout']['regimes'][0]['linked'])} linked return versus {pct(result['score']['regimes'][0]['linked'])} for Score. <b>Falling:</b> Score returned {pct(result['score']['regimes'][-1]['linked'])} versus {pct(result['breakout']['regimes'][-1]['linked'])} for Breakout. <b>Rising:</b> Score returned {pct(result['score']['regimes'][1]['linked'])} versus {pct(result['breakout']['regimes'][1]['linked'])} for Breakout."),
        p(f"The revised groups are more balanced ({meta['regime_counts'][-1]} falling, {meta['regime_counts'][0]} static, {meta['regime_counts'][1]} rising), but the experiment remains short. Breakout's stronger ending result came with {result['breakout']['replacements']} replacements, {tao(result['breakout']['costs'])} of realized modeled costs, and {pct(result['breakout']['max_drawdown'])} maximum drawdown. Score traded far less but also ended with a lower return.", "CautionX"),
        p("Method", "H2X"),
        p("Overall return uses liquidation NAV relative to the invariant 100 TAO start. Condition returns geometrically link the hourly NAV returns assigned to each contemporaneous Tao regime. P/L is the arithmetic NAV change across those intervals. The first sample has no condition. Values may differ slightly because of rounding.", "SmallX"),
    ]
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=.7*inch, rightMargin=.7*inch, topMargin=.62*inch, bottomMargin=.7*inch, title="SRBbot brief performance update under ±1% Tao conditions", author="Codex")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.db, args.output)
