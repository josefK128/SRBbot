from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import mean, median, pstdev

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
STRATEGIES = ("score", "breakout", "conditional")
REGIMES = ((-1, "Falling"), (0, "Static"), (1, "Rising"))

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2878A5")
ORANGE = colors.HexColor("#D07A28")
GREEN = colors.HexColor("#2D8363")
RED = colors.HexColor("#B34B4B")
GRAY = colors.HexColor("#5D6873")
BODY = colors.HexColor("#263440")
GRID = colors.HexColor("#D7DEE5")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_GREEN = colors.HexColor("#EAF6F1")
PALE_AMBER = colors.HexColor("#FFF4E2")
SERIES_COLORS = (BLUE, ORANGE, GREEN)


def dec(value) -> Decimal:
    return Decimal(str(value))


def pct(value: Decimal | None, places: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{places}f}%"


def tao(value: Decimal | None, places: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{places}f} TAO"


def linked(returns: list[Decimal]) -> Decimal | None:
    if not returns:
        return None
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


def load(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    snapshots = con.execute(
        "SELECT snapshot_id,sampled_at,tao_price_usd,tao_price_change,tao_market "
        "FROM snapshots ORDER BY sampled_at"
    ).fetchall()
    nav = con.execute(
        "SELECT s.sampled_at,n.* FROM positions_nav n JOIN snapshots s USING(snapshot_id) "
        "ORDER BY n.strategy,s.sampled_at"
    ).fetchall()
    decisions = con.execute(
        "SELECT s.sampled_at,s.tao_market,d.* FROM decisions d "
        "JOIN snapshots s USING(snapshot_id) ORDER BY d.strategy,s.sampled_at"
    ).fetchall()
    fills = con.execute(
        "SELECT d.strategy,s.sampled_at,f.side,f.netuid,f.tao_rao,f.fee_rao "
        "FROM fills f JOIN decisions d ON d.id=f.decision_id "
        "JOIN snapshots s ON s.snapshot_id=d.snapshot_id ORDER BY s.sampled_at"
    ).fetchall()
    con.close()
    return snapshots, nav, decisions, fills


def analyze(db_path: Path):
    snapshots, nav_rows, decisions, fills = load(db_path)
    by_nav = defaultdict(list)
    by_decision = defaultdict(list)
    by_fill = defaultdict(list)
    for row in nav_rows:
        by_nav[row["strategy"]].append(row)
    for row in decisions:
        by_decision[row["strategy"]].append(row)
    for row in fills:
        by_fill[row["strategy"]].append(row)

    if not snapshots or any(len(by_nav[s]) != len(snapshots) for s in STRATEGIES):
        raise RuntimeError("incomplete strategy coverage in cutoff database")

    start_price = dec(snapshots[0]["tao_price_usd"])
    end_price = dec(snapshots[-1]["tao_price_usd"])
    results = {}
    interval_map = {}
    daily = defaultdict(lambda: defaultdict(list))
    for strategy in STRATEGIES:
        rows = by_nav[strategy]
        navs = [dec(r["nav_rao"]) / TAO for r in rows]
        intervals = []
        for previous, current in zip(rows, rows[1:]):
            ret = dec(current["nav_rao"]) / dec(previous["nav_rao"]) - Decimal(1)
            at = datetime.fromisoformat(current["sampled_at"])
            item = {
                "at": at,
                "regime": current["tao_market"],
                "return": ret,
                "delta": (dec(current["nav_rao"]) - dec(previous["nav_rao"])) / TAO,
            }
            intervals.append(item)
            daily[at.date().isoformat()][strategy].append(ret)
        interval_map[strategy] = intervals
        acts = by_decision[strategy]
        fs = by_fill[strategy]
        ending = navs[-1]
        returns = [x["return"] for x in intervals]
        results[strategy] = {
            "navs": navs,
            "ending": ending,
            "pnl": ending - Decimal(100),
            "return": (ending / Decimal(100) - Decimal(1)) * Decimal(100),
            "usd_return": (ending * end_price / (Decimal(100) * start_price) - Decimal(1)) * Decimal(100),
            "drawdown": max_drawdown(navs),
            "vol": dec(pstdev([float(x * 100) for x in returns])),
            "win_rate": dec(sum(x > 0 for x in returns)) / dec(len(returns)) * 100,
            "best": max(returns) * 100,
            "worst": min(returns) * 100,
            "entries": sum(x["action"] == "ENTER" for x in acts),
            "replacements": sum(x["action"] == "REPLACE" for x in acts),
            "holds": sum(x["action"] == "HOLD" for x in acts),
            "turnover": sum((dec(x["tao_rao"]) for x in fs), Decimal(0)) / TAO,
            "fees": sum((dec(x["fee_rao"]) for x in fs), Decimal(0)) / TAO,
            "unique": len({x["netuid"] for x in fs if x["side"] == "STAKE"}),
            "held": rows[-1]["held_netuid"],
            "regimes": {},
        }
        for code, name in REGIMES:
            selected = [x for x in intervals if x["regime"] == code]
            rr = [x["return"] for x in selected]
            results[strategy]["regimes"][code] = {
                "name": name,
                "n": len(selected),
                "linked": linked(rr),
                "pnl": sum((x["delta"] for x in selected), Decimal(0)),
                "mean": mean(rr) * 100 if rr else None,
                "vol": dec(pstdev([float(x * 100) for x in rr])) if len(rr) > 1 else None,
                "win": dec(sum(x > 0 for x in rr)) / dec(len(rr)) * 100 if rr else None,
                "best": max(rr) * 100 if rr else None,
                "worst": min(rr) * 100 if rr else None,
            }

    times = [datetime.fromisoformat(x["sampled_at"]) for x in snapshots]
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(times, times[1:])]
    regime_counts = {code: sum(x["tao_market"] == code for x in snapshots[1:]) for code, _ in REGIMES}
    meta = {
        "samples": len(snapshots),
        "intervals": len(snapshots) - 1,
        "start": times[0],
        "end": times[-1],
        "hours": dec((times[-1] - times[0]).total_seconds() / 3600),
        "median_gap": dec(median(gaps)),
        "max_gap": dec(max(gaps)),
        "gaps_over_2h": sum(x > 2 for x in gaps),
        "start_price": start_price,
        "end_price": end_price,
        "tao_usd_return": (end_price / start_price - Decimal(1)) * 100,
        "regime_counts": regime_counts,
    }
    daily_rows = []
    for date in sorted(daily):
        daily_rows.append((date, *(linked(daily[date][s]) for s in STRATEGIES)))
    return meta, results, daily_rows


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=NAVY, alignment=TA_LEFT, spaceAfter=4))
styles.add(ParagraphStyle(name="SubtitleX", parent=styles["Normal"], fontSize=9.2, leading=12, textColor=GRAY, spaceAfter=11))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13.5, leading=16, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.2, leading=12.5, textColor=BLUE, spaceBefore=6, spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontSize=8.7, leading=12, textColor=BODY, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=7.1, leading=9.2, textColor=GRAY))
styles.add(ParagraphStyle(name="CellX", parent=styles["BodyText"], fontSize=7.2, leading=8.8, textColor=BODY))
styles.add(ParagraphStyle(name="HeaderX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.1, leading=8.6, textColor=colors.white))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontSize=9, leading=12.4, textColor=NAVY, backColor=PALE_GREEN, borderColor=GREEN, borderWidth=.7, borderPadding=8, spaceAfter=8))
styles.add(ParagraphStyle(name="CautionX", parent=styles["BodyText"], fontSize=8.5, leading=11.8, textColor=NAVY, backColor=PALE_AMBER, borderColor=ORANGE, borderWidth=.7, borderPadding=8, spaceAfter=8))
styles.add(ParagraphStyle(name="NoteX", parent=styles["BodyText"], fontSize=8.4, leading=11.5, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=.7, borderPadding=8, spaceAfter=8))


def p(text, style="BodyX"):
    return Paragraph(str(text), styles[style])


def table(rows, widths, aligns=None, shade_best=False):
    cooked = [[p(v, "HeaderX" if ri == 0 else "CellX") for v in row] for ri, row in enumerate(rows)]
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), .42, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    for row_index in range(2, len(rows), 2):
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F7F9FB")))
    if aligns:
        for index, align in enumerate(aligns):
            commands.append(("ALIGN", (index, 1), (index, -1), align))
    if shade_best:
        commands.append(("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#EEF8F4")))
    return Table(cooked, colWidths=widths, repeatRows=1, style=TableStyle(commands))


def nav_chart(results):
    drawing = Drawing(505, 190)
    chart = HorizontalLineChart()
    chart.x, chart.y, chart.width, chart.height = 48, 30, 430, 128
    chart.data = [[float(x) for x in results[s]["navs"]] for s in STRATEGIES]
    for index, color in enumerate(SERIES_COLORS):
        chart.lines[index].strokeColor = color
        chart.lines[index].strokeWidth = 1.8
    chart.categoryAxis.categoryNames = [str(i) if i % 12 == 0 else "" for i in range(len(results["score"]["navs"]))]
    chart.categoryAxis.labels.fontSize = 6
    all_values = [v for s in STRATEGIES for v in results[s]["navs"]]
    chart.valueAxis.valueMin = float(min(all_values)) - 1
    chart.valueAxis.valueMax = float(max(all_values)) + 1
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.0f"
    chart.valueAxis.gridStrokeColor = GRID
    drawing.add(chart)
    drawing.add(String(176, 176, "Liquidation NAV across accepted samples", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    drawing.add(String(48, 166, "Score", fontSize=7, fillColor=BLUE))
    drawing.add(String(91, 166, "Breakout", fontSize=7, fillColor=ORANGE))
    drawing.add(String(146, 166, "Conditional", fontSize=7, fillColor=GREEN))
    drawing.add(String(201, 5, "Accepted sample sequence", fontSize=7, fillColor=GRAY))
    return drawing


def regime_chart(results):
    drawing = Drawing(505, 185)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 50, 34, 425, 118
    chart.data = [[float(results[s]["regimes"][c]["linked"] or 0) for c, _ in REGIMES] for s in STRATEGIES]
    chart.categoryAxis.categoryNames = [name for _, name in REGIMES]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.0f%%"
    chart.valueAxis.gridStrokeColor = GRID
    for index, color in enumerate(SERIES_COLORS):
        chart.bars[index].fillColor = color
    chart.barSpacing = 1.5
    chart.groupSpacing = 11
    drawing.add(chart)
    drawing.add(String(169, 169, "Linked return by TAO-price regime", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    drawing.add(String(50, 160, "Score", fontSize=7, fillColor=BLUE))
    drawing.add(String(91, 160, "Breakout", fontSize=7, fillColor=ORANGE))
    drawing.add(String(146, 160, "Conditional", fontSize=7, fillColor=GREEN))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(.7 * inch, .55 * inch, 7.8 * inch, .55 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(.7 * inch, .36 * inch, "SRBbot Test 2 - final analysis")
    canvas.drawRightString(7.8 * inch, .36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(db_path: Path, output: Path):
    meta, r, daily_rows = analyze(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = meta["start"].strftime("%b %d, %Y %H:%M UTC")
    end = meta["end"].strftime("%b %d, %Y %H:%M UTC")
    rank = sorted(STRATEGIES, key=lambda s: r[s]["ending"], reverse=True)
    leader = rank[0]
    second = rank[1]
    lead = r[leader]["ending"] - r[second]["ending"]
    directional = meta["regime_counts"][-1] + meta["regime_counts"][1]
    story = [
        p("SRBbot Test 2 - final analysis", "TitleX"),
        p(f"Score, Breakout, and Conditional | {start} to {end} | Simulation-only", "SubtitleX"),
        p(
            f"<b>Decision summary:</b> {leader.title()} finished first at <b>{r[leader]['ending']:.3f} TAO</b> "
            f"({pct(r[leader]['return'])}), ahead of {second.title()} by {lead:.3f} TAO. "
            f"The test therefore supports <b>{leader.title()} as the final policy</b>, with cautious deployment because even the winner lost "
            f"{abs(r[leader]['pnl']):.3f} TAO and drew down {abs(r[leader]['drawdown']):.2f}%. This is a six-day paper test, not proof of live profitability.",
            "CalloutX",
        ),
        p("1 | Test coverage", "H1X"),
        table([
            ["Window", "Samples", "Intervals", "Elapsed", "Median gap"],
            [f"{start}<br/>to {end}", meta["samples"], meta["intervals"], f"{meta['hours']:.1f} h", f"{meta['median_gap']:.2f} h"],
        ], [2.75*inch, .65*inch, .65*inch, .8*inch, .9*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 7),
        table([
            ["TAO-price condition", "Definition", "Intervals", "Share"],
            ["Falling", "change < -1%", meta["regime_counts"][-1], pct(dec(meta["regime_counts"][-1]) / dec(meta["intervals"]) * 100, 1)],
            ["Static", "change in [-1%, +1%]", meta["regime_counts"][0], pct(dec(meta["regime_counts"][0]) / dec(meta["intervals"]) * 100, 1)],
            ["Rising", "change > +1%", meta["regime_counts"][1], pct(dec(meta["regime_counts"][1]) / dec(meta["intervals"]) * 100, 1)],
        ], [1.35*inch, 2.35*inch, .9*inch, .9*inch], ["LEFT", "LEFT", "RIGHT", "RIGHT"]),
        Spacer(1, 6),
        p(
            f"Coverage is complete: all three strategies have one NAV and one decision for every accepted snapshot. "
            f"There were {meta['gaps_over_2h']} gaps longer than two hours; the longest was {meta['max_gap']:.2f} hours. "
            f"Regime evidence is usable but uneven: {directional} directional intervals versus {meta['regime_counts'][0]} static intervals.",
            "CautionX",
        ),
        p("2 | Overall scorecard", "H1X"),
        table([
            ["Metric", "Score", "Breakout", "Conditional"],
            ["Ending liquidation NAV", tao(r["score"]["ending"]), tao(r["breakout"]["ending"]), tao(r["conditional"]["ending"])],
            ["Net return / P&L", f"{pct(r['score']['return'])} / {tao(r['score']['pnl'])}", f"{pct(r['breakout']['return'])} / {tao(r['breakout']['pnl'])}", f"{pct(r['conditional']['return'])} / {tao(r['conditional']['pnl'])}"],
            ["USD return incl. TAO move", pct(r["score"]["usd_return"]), pct(r["breakout"]["usd_return"]), pct(r["conditional"]["usd_return"])],
            ["Maximum drawdown", pct(r["score"]["drawdown"]), pct(r["breakout"]["drawdown"]), pct(r["conditional"]["drawdown"])],
            ["Interval volatility", pct(r["score"]["vol"]), pct(r["breakout"]["vol"]), pct(r["conditional"]["vol"])],
            ["Positive-interval rate", pct(r["score"]["win_rate"], 1), pct(r["breakout"]["win_rate"], 1), pct(r["conditional"]["win_rate"], 1)],
            ["Best / worst interval", f"{pct(r['score']['best'])} / {pct(r['score']['worst'])}", f"{pct(r['breakout']['best'])} / {pct(r['breakout']['worst'])}", f"{pct(r['conditional']['best'])} / {pct(r['conditional']['worst'])}"],
        ], [2.05*inch, 1.35*inch, 1.35*inch, 1.35*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 6),
        nav_chart(r),
        PageBreak(),
        p("3 | Trading activity and implementation drag", "H1X"),
        table([
            ["Metric", "Score", "Breakout", "Conditional"],
            ["Replacements", r["score"]["replacements"], r["breakout"]["replacements"], r["conditional"]["replacements"]],
            ["Hold decisions", r["score"]["holds"], r["breakout"]["holds"], r["conditional"]["holds"]],
            ["Executed turnover", tao(r["score"]["turnover"], 1), tao(r["breakout"]["turnover"], 1), tao(r["conditional"]["turnover"], 1)],
            ["Realized modeled fees", tao(r["score"]["fees"]), tao(r["breakout"]["fees"]), tao(r["conditional"]["fees"])],
            ["Fees / initial capital", pct(r["score"]["fees"]), pct(r["breakout"]["fees"]), pct(r["conditional"]["fees"])],
            ["Distinct staked subnets", r["score"]["unique"], r["breakout"]["unique"], r["conditional"]["unique"]],
            ["Final subnet (netuid)", r["score"]["held"], r["breakout"]["held"], r["conditional"]["held"]],
        ], [2.15*inch, 1.32*inch, 1.32*inch, 1.32*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 7),
        p(
            f"Breakout replaced its stake {r['breakout']['replacements']} times - {r['breakout']['replacements']/max(r['score']['replacements'],1):.1f}x Score's count - "
            f"and paid {r['breakout']['fees']:.3f} TAO in modeled realized fees. Conditional reduced Breakout's replacement count by "
            f"{r['breakout']['replacements'] - r['conditional']['replacements']} and its modeled fees by {r['breakout']['fees'] - r['conditional']['fees']:.3f} TAO. "
            f"This is economically important: switching policy, not just subnet selection quality, materially shaped the result.",
            "NoteX",
        ),
        p("4 | Results by TAO-price condition", "H1X"),
        p("Returns below geometrically link only the strategy intervals belonging to each condition. P/L contribution is the arithmetic NAV change across those intervals; the three contributions sum to the post-entry NAV change. The remaining difference from total P/L is the initial entry drag. Linked condition returns do not add.", "BodyX"),
    ]
    regime_rows = [["Condition", "n", "Score return / P&L", "Breakout return / P&L", "Conditional return / P&L"]]
    for code, name in REGIMES:
        regime_rows.append([
            name,
            r["score"]["regimes"][code]["n"],
            f"{pct(r['score']['regimes'][code]['linked'])} / {tao(r['score']['regimes'][code]['pnl'])}",
            f"{pct(r['breakout']['regimes'][code]['linked'])} / {tao(r['breakout']['regimes'][code]['pnl'])}",
            f"{pct(r['conditional']['regimes'][code]['linked'])} / {tao(r['conditional']['regimes'][code]['pnl'])}",
        ])
    story += [
        table(regime_rows, [1.0*inch, .35*inch, 1.55*inch, 1.55*inch, 1.55*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 5),
        regime_chart(r),
    ]
    for code, name in REGIMES:
        rows = [["Metric", "Score", "Breakout", "Conditional"]]
        for label, key, places in (
            ("Linked return", "linked", 2),
            ("Mean interval return", "mean", 3),
            ("Positive-interval rate", "win", 1),
            ("Interval volatility", "vol", 3),
            ("Best interval", "best", 2),
            ("Worst interval", "worst", 2),
        ):
            rows.append([label, *(pct(r[s]["regimes"][code][key], places) for s in STRATEGIES)])
        n = r["score"]["regimes"][code]["n"]
        rating = "moderate descriptive evidence" if n >= 20 else "limited descriptive evidence"
        story.append(KeepTogether([
            p(f"{name} ({n} intervals)", "H2X"),
            table(rows, [2.15*inch, 1.32*inch, 1.32*inch, 1.32*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT"]),
            p(f"Evidence rating: {rating}; no inferential claim is made.", "SmallX"),
            Spacer(1, 4),
        ]))
    story += [
        KeepTogether([
            p("5 | Day-by-day consistency", "H1X"),
            p("Daily rows are UTC calendar buckets. The first and last days are partial; use them for path inspection, not equal-duration comparison.", "BodyX"),
            table(
                [["UTC date", "Score", "Breakout", "Conditional"]] +
                [[date, pct(s), pct(b), pct(c)] for date, s, b, c in daily_rows],
                [2.0*inch, 1.35*inch, 1.35*inch, 1.35*inch],
                ["LEFT", "RIGHT", "RIGHT", "RIGHT"],
            ),
        ]),
        Spacer(1, 8),
        p("6 | Policy decision", "H1X"),
    ]

    conditional_is_best = leader == "conditional"
    if conditional_is_best:
        decision_text = (
            f"<b>Recommended final policy: Conditional.</b> It produced the highest ending NAV ({r['conditional']['ending']:.3f} TAO), "
            f"with {r['conditional']['replacements']} replacements versus Breakout's {r['breakout']['replacements']}, and a maximum drawdown of "
            f"{pct(r['conditional']['drawdown'])}. The result supports using Score when TAO is static or falling and Breakout only when TAO is rising above +1%."
        )
    else:
        decision_text = (
            f"<b>Recommended final policy: {leader.title()}.</b> It produced the highest ending NAV ({r[leader]['ending']:.3f} TAO). "
            f"Conditional finished at {r['conditional']['ending']:.3f} TAO, so the additional regime switch did not earn its complexity in this test."
        )
    story += [
        p(decision_text, "CalloutX"),
        p("Guardrails for adoption", "H2X"),
        p(
            "Treat this as a policy selection from a short paper experiment, not a live-capital forecast. Preserve the exact thresholds and fee model used here; begin with limited exposure; record live slippage separately from modeled fees; and set a review trigger if drawdown exceeds the paper-test maximum or replacement frequency materially exceeds this run.",
            "BodyX",
        ),
        p("What is genuinely informative", "H2X"),
        p(
            "The full-period ranking, drawdown, turnover, fees, and directional-regime splits are the most decision-relevant evidence. The comparison is internally clean because every strategy saw the same 122 snapshots and each began with 100 TAO. Conditional's path is stateful: its return is not a splice of Score and Breakout returns because switching affects which subnet it holds on later samples.",
            "BodyX",
        ),
        p("What remains uncertain", "H2X"),
        p(
            f"Only {meta['regime_counts'][1]} rising and {meta['regime_counts'][-1]} falling intervals were observed, while TAO itself moved from ${meta['start_price']:.2f} to ${meta['end_price']:.2f} ({pct(meta['tao_usd_return'])}). "
            "Results can be dominated by a few subnet moves, and paper fills cannot reveal capacity, latency, or real slippage. A future validation should freeze the chosen policy and test it out of sample without retuning the +1% boundary.",
            "CautionX",
        ),
        p("7 | Method", "H1X"),
        p(
            "Source is a point-in-time copy of the SRBbot SQLite journal at the report cutoff. Each strategy starts with 100 TAO. Liquidation NAV marks the held subnet at each accepted snapshot under the simulator's fee assumptions. Overall return is ending NAV / 100 - 1. USD return applies the contemporaneous TAO/USD price to ending TAO NAV and compares it with 100 TAO at the opening TAO/USD price. Maximum drawdown is the largest peak-to-trough decline in recorded liquidation NAV. Interval volatility is the population standard deviation of per-sample percentage returns and is not annualized. Regimes use the ending snapshot's recorded TAO price change: rising > +1%, static in [-1%, +1%], falling < -1%. P/L contributions are arithmetic NAV changes for the intervals in each regime. Reported fees are realized fill fees; liquidation NAV may also reflect hypothetical exit cost. Rounded figures may not recompute exactly.",
            "SmallX",
        ),
    ]

    doc = SimpleDocTemplate(
        str(output), pagesize=letter, leftMargin=.7*inch, rightMargin=.7*inch,
        topMargin=.62*inch, bottomMargin=.7*inch,
        title="SRBbot Test 2 - final strategy analysis", author="Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.db, args.output)
