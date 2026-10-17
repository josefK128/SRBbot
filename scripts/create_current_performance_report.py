from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import mean, pstdev

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


TAO = Decimal("1000000000")
REGIMES = [(-1, "Falling"), (0, "Static"), (1, "Rising")]
NAVY = colors.HexColor("#18324A")
BLUE = colors.HexColor("#2D6F9F")
ORANGE = colors.HexColor("#D07A28")
GREEN = colors.HexColor("#277A53")
RED = colors.HexColor("#B34B4B")
GRAY = colors.HexColor("#5D6873")
GRID = colors.HexColor("#D4DCE3")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF3DF")


def d(value) -> Decimal:
    return Decimal(str(value))


def pct(value: Decimal, places: int = 3) -> str:
    return f"{value:.{places}f}%"


def tao(value: Decimal, places: int = 4) -> str:
    return f"{value:.{places}f} TAO"


def linked_return(returns: list[Decimal]) -> Decimal:
    result = Decimal(1)
    for item in returns:
        result *= Decimal(1) + item
    return (result - Decimal(1)) * Decimal(100)


def max_drawdown(values: list[Decimal]) -> Decimal:
    peak = values[0]
    worst = Decimal(0)
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - Decimal(1))
    return worst * Decimal(100)


def load_data(db_path: Path):
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    snapshots = con.execute(
        "SELECT snapshot_id,sampled_at,tao_price_usd,tao_price_change,tao_market "
        "FROM snapshots ORDER BY sampled_at"
    ).fetchall()
    nav_rows = con.execute(
        "SELECT s.sampled_at,n.* FROM positions_nav n JOIN snapshots s USING(snapshot_id) "
        "ORDER BY n.strategy,s.sampled_at"
    ).fetchall()
    decisions = con.execute(
        "SELECT d.*,s.sampled_at,s.tao_market FROM decisions d "
        "JOIN snapshots s USING(snapshot_id) ORDER BY s.sampled_at,d.strategy"
    ).fetchall()
    fills = con.execute(
        "SELECT d.strategy,f.side,f.tao_rao,f.fee_rao FROM fills f "
        "JOIN decisions d ON d.id=f.decision_id"
    ).fetchall()
    portfolios = con.execute("SELECT * FROM portfolios ORDER BY strategy").fetchall()
    con.close()
    return snapshots, nav_rows, decisions, fills, portfolios


def analyze(db_path: Path):
    snapshots, nav_rows, decisions, fills, portfolios = load_data(db_path)
    nav_by_strategy = defaultdict(list)
    for row in nav_rows:
        nav_by_strategy[row["strategy"]].append(row)
    decision_by_strategy = defaultdict(list)
    for row in decisions:
        decision_by_strategy[row["strategy"]].append(row)
    fill_by_strategy = defaultdict(list)
    for row in fills:
        fill_by_strategy[row["strategy"]].append(row)

    result = {}
    interval_data = {}
    for strategy in ("score", "breakout"):
        rows = nav_by_strategy[strategy]
        navs = [d(row["nav_rao"]) / TAO for row in rows]
        intervals = []
        for previous, current in zip(rows, rows[1:]):
            ret = d(current["nav_rao"]) / d(previous["nav_rao"]) - Decimal(1)
            intervals.append(
                {
                    "sampled_at": current["sampled_at"],
                    "regime": current["tao_market"],
                    "return": ret,
                    "delta_tao": (d(current["nav_rao"]) - d(previous["nav_rao"])) / TAO,
                }
            )
        interval_data[strategy] = intervals
        actions = decision_by_strategy[strategy]
        strategy_fills = fill_by_strategy[strategy]
        initial = Decimal(100)
        end = navs[-1]
        result[strategy] = {
            "navs": navs,
            "rows": rows,
            "ending_nav": end,
            "return": (end / initial - Decimal(1)) * Decimal(100),
            "pnl": end - initial,
            "max_drawdown": max_drawdown(navs),
            "up_hours": sum(1 for x in intervals if x["return"] > 0),
            "down_hours": sum(1 for x in intervals if x["return"] < 0),
            "flat_hours": sum(1 for x in intervals if x["return"] == 0),
            "replacements": sum(1 for x in actions if x["action"] == "REPLACE"),
            "entries": sum(1 for x in actions if x["action"] == "ENTER"),
            "holds": sum(1 for x in actions if x["action"] == "HOLD"),
            "costs": sum(d(x["fee_rao"]) for x in strategy_fills) / TAO,
            "turnover": sum(d(x["tao_rao"]) for x in strategy_fills) / TAO,
            "held": rows[-1]["held_netuid"],
        }
        regime_stats = {}
        for code, name in REGIMES:
            selected = [x for x in intervals if x["regime"] == code]
            returns = [x["return"] for x in selected]
            regime_stats[code] = {
                "name": name,
                "n": len(selected),
                "linked": linked_return(returns) if returns else None,
                "mean": mean(returns) * 100 if returns else None,
                "vol": d(pstdev([float(x * 100) for x in returns])) if len(returns) > 1 else None,
                "win_rate": d(sum(1 for x in returns if x > 0)) / d(len(returns)) * 100 if returns else None,
                "delta_tao": sum((x["delta_tao"] for x in selected), Decimal(0)),
            }
        result[strategy]["regimes"] = regime_stats

    tao_prices = [d(x["tao_price_usd"]) for x in snapshots]
    meta = {
        "count": len(snapshots),
        "intervals": len(snapshots) - 1,
        "start": snapshots[0]["sampled_at"],
        "end": snapshots[-1]["sampled_at"],
        "tao_start": tao_prices[0],
        "tao_end": tao_prices[-1],
        "tao_return": (tao_prices[-1] / tao_prices[0] - Decimal(1)) * 100,
        "regime_counts": {code: sum(1 for x in snapshots[1:] if x["tao_market"] == code) for code, _ in REGIMES},
    }
    return meta, result


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=GRAY, spaceAfter=12))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=6, spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontSize=9, leading=12.5, textColor=colors.HexColor("#263440"), spaceAfter=6))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.3, leading=9.4, textColor=GRAY))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontSize=9.2, leading=13, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=.7, borderPadding=8, spaceAfter=9))
styles.add(ParagraphStyle(name="Caution", parent=styles["BodyText"], fontSize=8.8, leading=12.5, textColor=NAVY, backColor=PALE_AMBER, borderColor=ORANGE, borderWidth=.7, borderPadding=8, spaceBefore=4, spaceAfter=9))


def cell(text, bold=False, color=None):
    return Paragraph(str(text), ParagraphStyle(name="cell", parent=styles["Small"], fontName="Helvetica-Bold" if bold else "Helvetica", textColor=color or colors.HexColor("#263440")))


def table(rows, widths, aligns=None):
    cooked = []
    for ri, row in enumerate(rows):
        cooked.append([cell(v, bold=(ri == 0), color=(colors.white if ri == 0 else None)) for v in row])
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), .45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if aligns:
        for index, align in enumerate(aligns):
            commands.append(("ALIGN", (index, 1), (index, -1), align))
    return Table(cooked, colWidths=widths, repeatRows=1, style=TableStyle(commands))


def nav_chart(score, breakout):
    drawing = Drawing(505, 190)
    chart = HorizontalLineChart()
    chart.x, chart.y, chart.width, chart.height = 48, 30, 430, 130
    chart.data = [[float(x) for x in score], [float(x) for x in breakout]]
    chart.lines[0].strokeColor = BLUE; chart.lines[0].strokeWidth = 2
    chart.lines[1].strokeColor = ORANGE; chart.lines[1].strokeWidth = 2
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.categoryNames = [str(i) if i % 6 == 0 else "" for i in range(len(score))]
    chart.valueAxis.valueMin = min(float(min(score)), float(min(breakout))) - .4
    chart.valueAxis.valueMax = max(float(max(score)), float(max(breakout))) + .4
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.1f"
    chart.valueAxis.gridStrokeColor = GRID
    drawing.add(chart)
    drawing.add(String(190, 177, "Liquidation NAV (TAO) by accepted sample", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    drawing.add(String(180, 5, "Sample sequence (approximately hourly)", fontSize=7, fillColor=GRAY))
    drawing.add(String(50, 174, "Score", fontSize=7, fillColor=BLUE))
    drawing.add(String(95, 174, "Breakout", fontSize=7, fillColor=ORANGE))
    return drawing


def regime_chart(result):
    drawing = Drawing(505, 180)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 50, 35, 425, 115
    chart.data = [
        [float(result["score"]["regimes"][code]["linked"] or 0) for code, _ in REGIMES],
        [float(result["breakout"]["regimes"][code]["linked"] or 0) for code, _ in REGIMES],
    ]
    chart.categoryAxis.categoryNames = [name for _, name in REGIMES]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.2f%%"
    chart.valueAxis.gridStrokeColor = GRID
    chart.bars[0].fillColor = BLUE; chart.bars[1].fillColor = ORANGE
    chart.barSpacing = 2; chart.groupSpacing = 12
    drawing.add(chart)
    drawing.add(String(160, 165, "Linked strategy return by Tao regime", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    drawing.add(String(50, 158, "Score", fontSize=7, fillColor=BLUE))
    drawing.add(String(95, 158, "Breakout", fontSize=7, fillColor=ORANGE))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID); canvas.line(.7 * inch, .55 * inch, 7.8 * inch, .55 * inch)
    canvas.setFont("Helvetica", 7); canvas.setFillColor(GRAY)
    canvas.drawString(.7 * inch, .36 * inch, "SRBbot current performance analysis")
    canvas.drawRightString(7.8 * inch, .36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(db_path: Path, output: Path):
    meta, result = analyze(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.fromisoformat(meta["start"]).strftime("%b %d, %Y %H:%M UTC")
    end = datetime.fromisoformat(meta["end"]).strftime("%b %d, %Y %H:%M UTC")
    leader = "Score" if result["score"]["ending_nav"] > result["breakout"]["ending_nav"] else "Breakout"
    gap = abs(result["score"]["ending_nav"] - result["breakout"]["ending_nav"])
    story = [
        Paragraph("SRBbot current performance", styles["ReportTitle"]),
        Paragraph(f"Score vs. Breakout | Cutoff: {end} | Simulation-only, 100 TAO per strategy", styles["Subtitle"]),
        Paragraph(
            f"<b>Current read:</b> {leader} leads by {gap:.4f} TAO. Score is at {result['score']['ending_nav']:.4f} TAO "
            f"({pct(result['score']['return'])}); Breakout is at {result['breakout']['ending_nav']:.4f} TAO "
            f"({pct(result['breakout']['return'])}). This is an early, highly regime-imbalanced sample, so the result is descriptive rather than conclusive.",
            styles["Callout"],
        ),
        Paragraph("1 | Experiment coverage", styles["H1x"]),
        table([
            ["Window", "Samples", "Intervals", "Tao price", "Tao change"],
            [f"{start} to {end}", meta["count"], meta["intervals"], f"${meta['tao_start']:.2f} -> ${meta['tao_end']:.2f}", pct(meta["tao_return"], 2)],
        ], [2.55*inch, .7*inch, .72*inch, 1.5*inch, 1.0*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 8),
        table([
            ["Tao condition", "Rule", "Observed intervals", "Share"],
            ["Falling (-1)", "hourly Tao move < -1%", meta["regime_counts"][-1], pct(d(meta["regime_counts"][-1]) / d(meta["intervals"]) * 100, 1)],
            ["Static (0)", "hourly Tao move within [-1%, +1%]", meta["regime_counts"][0], pct(d(meta["regime_counts"][0]) / d(meta["intervals"]) * 100, 1)],
            ["Rising (+1)", "hourly Tao move > +1%", meta["regime_counts"][1], pct(d(meta["regime_counts"][1]) / d(meta["intervals"]) * 100, 1)],
        ], [1.25*inch, 2.55*inch, 1.25*inch, 1.0*inch], ["LEFT", "LEFT", "RIGHT", "RIGHT"]),
        Spacer(1, 8),
        Paragraph("The first snapshot establishes the comparison base and has no Tao condition. Performance by condition therefore uses the following 48 interval returns, classified by the condition recorded on each interval's ending snapshot.", styles["Small"]),
        Paragraph("2 | Overall performance", styles["H1x"]),
        table([
            ["Metric", "Score", "Breakout"],
            ["Ending liquidation NAV", tao(result["score"]["ending_nav"]), tao(result["breakout"]["ending_nav"])],
            ["Net return from 100 TAO", pct(result["score"]["return"]), pct(result["breakout"]["return"])],
            ["Net P/L", tao(result["score"]["pnl"]), tao(result["breakout"]["pnl"])],
            ["Maximum drawdown", pct(result["score"]["max_drawdown"]), pct(result["breakout"]["max_drawdown"])],
            ["Positive / negative / flat intervals", f"{result['score']['up_hours']} / {result['score']['down_hours']} / {result['score']['flat_hours']}", f"{result['breakout']['up_hours']} / {result['breakout']['down_hours']} / {result['breakout']['flat_hours']}"],
            ["Replacements (plus initial entry)", f"{result['score']['replacements']} (+1)", f"{result['breakout']['replacements']} (+1)"],
            ["Executed turnover", tao(result["score"]["turnover"], 2), tao(result["breakout"]["turnover"], 2)],
            ["Realized modeled costs", tao(result["score"]["costs"], 4), tao(result["breakout"]["costs"], 4)],
            ["Current subnet", result["score"]["held"], result["breakout"]["held"]],
        ], [2.8*inch, 1.65*inch, 1.65*inch], ["LEFT", "RIGHT", "RIGHT"]),
        Spacer(1, 6), nav_chart(result["score"]["navs"], result["breakout"]["navs"]),
        PageBreak(),
        Paragraph("3 | Performance by Tao market condition", styles["H1x"]),
        Paragraph("Linked returns compound only the hourly strategy returns observed within each condition. TAO contribution is the arithmetic change in liquidation NAV across those same intervals; it is useful for attribution but does not itself compound.", styles["Bodyx"]),
    ]
    regime_rows = [["Condition", "n", "Score linked", "Score P/L contrib.", "Breakout linked", "Breakout P/L contrib."]]
    for code, name in REGIMES:
        s = result["score"]["regimes"][code]; b = result["breakout"]["regimes"][code]
        regime_rows.append([name, s["n"], pct(s["linked"]) if s["linked"] is not None else "n/a", tao(s["delta_tao"]), pct(b["linked"]) if b["linked"] is not None else "n/a", tao(b["delta_tao"])])
    story += [
        table(regime_rows, [1.0*inch, .38*inch, 1.05*inch, 1.25*inch, 1.12*inch, 1.3*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 8), regime_chart(result),
    ]
    for code, name in REGIMES:
        s = result["score"]["regimes"][code]; b = result["breakout"]["regimes"][code]
        reliability = "insufficient for inference" if s["n"] < 5 else ("still preliminary" if s["n"] < 20 else "directionally informative")
        rows = [["Metric", "Score", "Breakout"], ["Intervals", s["n"], b["n"]], ["Linked return", pct(s["linked"]) if s["linked"] is not None else "n/a", pct(b["linked"]) if b["linked"] is not None else "n/a"], ["Mean interval return", pct(s["mean"]) if s["mean"] is not None else "n/a", pct(b["mean"]) if b["mean"] is not None else "n/a"], ["Positive-interval rate", pct(s["win_rate"], 1) if s["win_rate"] is not None else "n/a", pct(b["win_rate"], 1) if b["win_rate"] is not None else "n/a"], ["Interval volatility", pct(s["vol"]) if s["vol"] is not None else "n/a", pct(b["vol"]) if b["vol"] is not None else "n/a"]]
        story += [KeepTogether([Paragraph(f"{name} Tao market", styles["H2x"]), table(rows, [2.5*inch, 1.75*inch, 1.75*inch], ["LEFT", "RIGHT", "RIGHT"]), Paragraph(f"Evidence rating: <b>{reliability}</b>. The condition has only {s['n']} observed interval(s).", styles["Small"]), Spacer(1, 5)])]
    story += [
        PageBreak(), Paragraph("4 | Interpretation", styles["H1x"]),
        Paragraph("What the first half-week says", styles["H2x"]),
        Paragraph(
            f"The leader is {leader}, with an absolute separation of {gap:.4f} TAO. Score made {result['score']['replacements']} replacements versus {result['breakout']['replacements']} for Breakout; the resulting turnover and realized costs show how much of each strategy's result is being consumed by switching. Both strategies nevertheless experienced severe interim drawdowns of roughly 28%-31%, so the positive ending returns came with substantial path risk.", styles["Bodyx"]),
        Paragraph("The Tao-condition split is not balanced enough to rank robustness", styles["H2x"]),
        Spacer(1, 6),
        Paragraph(
            f"Static conditions account for {meta['regime_counts'][0]} of {meta['intervals']} measured intervals. Falling has {meta['regime_counts'][-1]} observations and rising has only {meta['regime_counts'][1]}. The filtered figures accurately describe these events, but a single rising hour and three falling hours cannot establish repeatable regime behavior.", styles["Caution"]),
        Paragraph("How to read the economics", styles["H2x"]),
        Paragraph("NAV is expressed in TAO and marked to the current subnet price after every accepted snapshot. It is a liquidation NAV: the model applies the hypothetical unstake cost when valuing the position, while the realized-cost figure counts fees actually booked on stake and unstake fills. Each strategy began with 100 TAO and trades independently.", styles["Bodyx"]),
        Paragraph("5 | Recommended next checkpoint", styles["H1x"]),
        Paragraph("Continue the frozen simulation through the planned one-week horizon. At the next review, repeat this report and focus on: (1) whether the overall leader persists, (2) whether drawdown grows faster than return, (3) whether replacement frequency and costs stabilize, and (4) whether falling and rising regimes accumulate enough observations to support comparison. Avoid strategy changes during the measurement window.", styles["Callout"]),
        Paragraph("Method and reproducibility", styles["H1x"]),
        Paragraph(f"Source: a consistent SQLite backup of the live SRBbot journal at the stated cutoff. Overall return is ending liquidation NAV divided by the invariant 100 TAO start balance. Maximum drawdown is peak-to-trough decline in recorded liquidation NAV. Condition returns are geometrically linked hourly NAV returns grouped by tao_market (-1, 0, +1). Turnover is the sum of recorded fill tao_rao; realized costs are the sum of recorded fill fee_rao. Values may differ slightly from displayed totals due to rounding.", styles["Small"]),
    ]
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=.7*inch, rightMargin=.7*inch, topMargin=.62*inch, bottomMargin=.7*inch, title="SRBbot current performance analysis", author="Codex")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.db, args.output)
