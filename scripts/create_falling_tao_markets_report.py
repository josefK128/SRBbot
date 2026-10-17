from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from srbbot.broker import CostModel
from srbbot.models import Observation, Snapshot
from srbbot.strategy import decide


TAO = Decimal("1000000000")
NAVY = colors.HexColor("#18324A")
BLUE = colors.HexColor("#2D6F9F")
ORANGE = colors.HexColor("#D07A28")
GREEN = colors.HexColor("#277A53")
GRAY = colors.HexColor("#5D6873")
GRID = colors.HexColor("#D4DCE3")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF3DF")
BODY = colors.HexColor("#263440")


def d(value) -> Decimal:
    return Decimal(str(value))


def pct(value: Decimal, places=3) -> str:
    return f"{value:.{places}f}%"


def tao(value: Decimal, places=4) -> str:
    return f"{value:.{places}f} TAO"


def linked(values: list[Decimal]) -> Decimal:
    result = Decimal(1)
    for value in values:
        result *= Decimal(1) + value
    return (result - Decimal(1)) * 100


def max_drawdown(values: list[Decimal]) -> Decimal:
    peak = values[0]
    worst = Decimal(0)
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return worst * 100


def load(db_path: Path):
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT snapshot_id,sampled_at,tao_price_usd,tao_price_change,tao_market "
        "FROM snapshots ORDER BY sampled_at"
    ).fetchall()
    snapshots = []
    markets = []
    for row in rows:
        observations = con.execute(
            "SELECT netuid,score,delta_price_1h,price_tao FROM observations "
            "WHERE snapshot_id=? ORDER BY netuid", (row["snapshot_id"],)
        ).fetchall()
        snapshots.append(Snapshot(
            snapshot_id=row["snapshot_id"],
            sampled_at=datetime.fromisoformat(row["sampled_at"]),
            tao_price_usd=d(row["tao_price_usd"]),
            observations=tuple(Observation(x["netuid"], d(x["score"]), d(x["delta_price_1h"]), d(x["price_tao"])) for x in observations),
        ))
        markets.append(row["tao_market"])
    con.close()
    return snapshots, markets


@dataclass
class Portfolio:
    free: int = 100_000_000_000
    held: int | None = None
    alpha: Decimal = Decimal(0)
    costs: int = 0
    turnover: int = 0
    switches: int = 0


def stake(portfolio: Portfolio, netuid: int, snapshot: Snapshot, costs: CostModel):
    price = snapshot.by_netuid()[netuid].price_tao
    before = portfolio.free
    portfolio.free, portfolio.alpha, fee = costs.stake(portfolio.free, price)
    portfolio.held = netuid
    portfolio.costs += fee
    portfolio.turnover += before - fee


def unstake(portfolio: Portfolio, snapshot: Snapshot, costs: CostModel):
    price = snapshot.by_netuid()[portfolio.held].price_tao
    proceeds, fee = costs.unstake(portfolio.alpha, price)
    portfolio.free += proceeds
    portfolio.costs += fee
    portfolio.turnover += proceeds + fee
    portfolio.held = None
    portfolio.alpha = Decimal(0)


def switch(portfolio: Portfolio, netuid: int, snapshot: Snapshot, costs: CostModel):
    if portfolio.held == netuid:
        return
    if portfolio.held is not None:
        unstake(portfolio, snapshot, costs)
    stake(portfolio, netuid, snapshot, costs)
    portfolio.switches += 1


def nav(portfolio: Portfolio, snapshot: Snapshot, costs: CostModel) -> Decimal:
    value = portfolio.free
    if portfolio.held is not None:
        value += costs.liquidation_value(portfolio.alpha, snapshot.by_netuid()[portfolio.held].price_tao)
    return d(value) / TAO


def candidate(snapshot: Snapshot, rule: str) -> int:
    if rule == "score":
        return max(snapshot.observations, key=lambda x: (x.score, -x.netuid)).netuid
    return max(snapshot.observations, key=lambda x: (x.delta_price_1h, -x.netuid)).netuid


def run_policy(snapshots, markets, falling_policy: str):
    costs = CostModel()
    portfolio = Portfolio()
    navs = []
    actions = []
    for index, (snapshot, market) in enumerate(zip(snapshots, markets)):
        if index == 0:
            switch(portfolio, candidate(snapshot, "score"), snapshot, costs)
            actions.append("initial-score")
        elif market == -1 and falling_policy == "hold":
            actions.append("falling-hold")
        elif market == -1 and falling_policy == "tao":
            if portfolio.held is not None:
                unstake(portfolio, snapshot, costs)
                portfolio.switches += 1
            actions.append("falling-tao")
        elif market == -1 and falling_policy == "sn51":
            switch(portfolio, 51, snapshot, costs)
            actions.append("falling-sn51")
        else:
            rule = "breakout" if market == 1 else "score"
            if portfolio.held is None:
                switch(portfolio, candidate(snapshot, rule), snapshot, costs)
                actions.append(f"enter-{rule}")
            else:
                decision = decide(snapshot, rule, portfolio.held)
                if decision.action == "REPLACE":
                    switch(portfolio, decision.candidate_netuid, snapshot, costs)
                actions.append(f"{rule}-{decision.action.lower()}")
        navs.append(nav(portfolio, snapshot, costs))
    return {
        "navs": navs,
        "ending": navs[-1],
        "return": (navs[-1] / 100 - 1) * 100,
        "drawdown": max_drawdown(navs),
        "costs": d(portfolio.costs) / TAO,
        "turnover": d(portfolio.turnover) / TAO,
        "switches": portfolio.switches - 1,
        "held": portfolio.held,
        "actions": actions,
    }


def next_interval_analysis(snapshots, markets):
    rows = {"TAO cash": [], "SN51": [], "Score candidate": [], "Breakout candidate": []}
    for index, market in enumerate(markets[:-1]):
        if market != -1:
            continue
        current, nxt = snapshots[index], snapshots[index + 1]
        current_obs, next_obs = current.by_netuid(), nxt.by_netuid()
        rows["TAO cash"].append(Decimal(0))
        for label, netuid in (
            ("SN51", 51),
            ("Score candidate", candidate(current, "score")),
            ("Breakout candidate", candidate(current, "breakout")),
        ):
            rows[label].append(next_obs[netuid].price_tao / current_obs[netuid].price_tao - 1)
    return {
        label: {
            "n": len(values),
            "linked": linked(values),
            "mean": sum(values, Decimal(0)) / len(values) * 100,
            "positive": d(sum(x > 0 for x in values)) / len(values) * 100,
            "worst": min(values) * 100,
        }
        for label, values in rows.items()
    }


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
    data = [[p(value, "HeaderX" if ri == 0 else "SmallX") for value in row] for ri, row in enumerate(rows)]
    commands = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), .45, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if aligns:
        for index, align in enumerate(aligns):
            commands.append(("ALIGN", (index, 1), (index, -1), align))
    return Table(data, colWidths=widths, repeatRows=1, style=TableStyle(commands))


def bar_chart(policies):
    labels = ["Score in fall", "Hold position", "Move to TAO", "Move to SN51"]
    keys = ["score", "hold", "tao", "sn51"]
    drawing = Drawing(500, 180)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 55, 35, 415, 115
    chart.data = [[float(policies[key]["return"]) for key in keys]]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 6.5
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.1f%%"
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 70
    chart.valueAxis.valueStep = 10
    chart.valueAxis.gridStrokeColor = GRID
    chart.bars[0].fillColor = BLUE
    drawing.add(chart)
    drawing.add(String(150, 165, "Whole-window return of Conditional variants", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(.7 * inch, .55 * inch, 7.8 * inch, .55 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(.7 * inch, .36 * inch, "SRBbot in falling Tao markets")
    canvas.drawRightString(7.8 * inch, .36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(db_path: Path, output: Path):
    snapshots, markets = load(db_path)
    policies = {key: run_policy(snapshots, markets, key) for key in ("score", "hold", "tao", "sn51")}
    next_results = next_interval_analysis(snapshots, markets)
    falling = sum(x == -1 for x in markets)
    end = snapshots[-1].sampled_at.strftime("%b %d, %Y %H:%M UTC")
    policy_names = {"score": "Use Score", "hold": "Hold current subnet", "tao": "Move to TAO", "sn51": "Move to SN51"}
    best = max(policies, key=lambda key: policies[key]["ending"])
    output.parent.mkdir(parents=True, exist_ok=True)
    story = [
        p("SRBbot in falling Tao markets", "TitleX"),
        p(f"Defensive-policy analysis for the proposed Conditional strategy | Cutoff: {end}", "SubtitleX"),
        p(f"<b>Preliminary conclusion:</b> In this short replay, <b>{policy_names[best]}</b> produced the highest whole-window Conditional NAV. Moving mechanically to TAO or SN51 after every falling signal was not automatically superior once timing and trading costs were included. The evidence covers only {falling} falling signals and should guide a forward test, not lock in a permanent defensive rule.", "CalloutX"),
        p("1 | The timing issue", "H1X"),
        p("A falling condition is known only when the new hourly sample arrives. The price move that created the signal has already occurred. A trade made at that sample can protect only against later movement; it cannot avoid the just-observed fall. Most falling signals in this dataset are isolated rather than long runs, so exiting and re-entering can pay two-sided costs without receiving much time in the defensive asset."),
        p("2 | Policies compared", "H1X"),
        table([
            ["Falling-period policy", "Action at a falling sample", "Action otherwise"],
            ["Use Score", "Apply the normal Score candidate and >10% signal hurdle", "Score when static; Breakout when rising"],
            ["Hold current subnet", "Make no replacement, regardless of Score signal", "Score when static; Breakout when rising"],
            ["Move to TAO", "Unstake and remain in liquid TAO", "Re-enter using Score or Breakout"],
            ["Move to SN51", "Force the portfolio into subnet 51", "Resume Score or Breakout rules"],
        ], [1.45*inch, 2.85*inch, 2.45*inch]),
        p("All four variants start with 100 TAO, use Score for the initial entry, use Breakout only when Tao rises by more than 1%, and use the frozen fee/slippage model. The comparison is a deterministic replay, not a change to the live bot.", "SmallX"),
        p("3 | Whole-window Conditional replay", "H1X"),
    ]
    rows = [["Falling policy", "Ending NAV", "Return", "Max drawdown", "Repl.", "Costs"]]
    for key in ("score", "hold", "tao", "sn51"):
        x = policies[key]
        rows.append([policy_names[key], tao(x["ending"]), pct(x["return"]), pct(x["drawdown"]), x["switches"], tao(x["costs"])])
    story += [
        table(rows, [1.35*inch, 1.05*inch, .82*inch, .95*inch, .82*inch, 1.0*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        Spacer(1, 5), bar_chart(policies),
        PageBreak(),
        p("4 | What happened after falling signals?", "H1X"),
        p("The table below asks a simpler, forward-looking question: after each falling signal, how did a position selected at that sample perform until the next sample? It excludes trading costs so that asset behavior can be seen separately from implementation costs."),
    ]
    next_rows = [["Asset selected after signal", "n", "Linked next-hour", "Mean next-hour", "Positive rate", "Worst hour"]]
    for label in ("TAO cash", "SN51", "Score candidate", "Breakout candidate"):
        x = next_results[label]
        next_rows.append([label, x["n"], pct(x["linked"]), pct(x["mean"]), pct(x["positive"], 1), pct(x["worst"])])
    story += [
        table(next_rows, [1.55*inch, .38*inch, 1.12*inch, 1.12*inch, 1.0*inch, .95*inch], ["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]),
        p("5 | Interpreting the choices", "H1X"),
        p("Move to TAO", "H2X"),
        p("TAO is the cleanest capital-preservation choice in TAO terms: its next-hour TAO return is 0%. But entering cash requires an unstake and leaving cash requires a new stake. With an approximately 0.60% modeled round trip plus network fees, a one-hour defensive move needs a meaningful avoided subnet loss merely to break even."),
        p("Hold the current subnet", "H2X"),
        p("Holding avoids churn and is sensible when the falling signal is likely to be brief. Its weakness is that it provides no deliberate defense against a continued selloff. Results depend on whichever subnet Conditional happened to own when the signal arrived."),
        p("Move to SN51", "H2X"),
        p("A large market capitalization can suggest liquidity or maturity, but it does not guarantee lower TAO-denominated downside. The SRB snapshots do not contain market-cap or liquidity fields, so this report tests SN51's observed price path rather than validating the market-cap premise. A forced SN51 rule also creates trades independent of Score strength."),
        p("Use Score", "H2X"),
        p("This is the simplest version of Conditional and matches the agreed rule: Score for all Tao changes at or below +1%, Breakout above +1%. It preserves the existing >10% Score replacement hurdle, so it can either hold or rotate based on relative signal strength instead of forcing a defensive asset."),
        p("6 | Recommendation for Conditional", "H1X"),
        p("Start the forward Conditional test with the simple agreed rule: <b>Score when Tao change is <= +1%; Breakout when it is > +1%</b>. Do not add an automatic SN51 move yet. In parallel, log three shadow comparisons during falling periods: hold-current, move-to-TAO, and move-to-SN51. Reconsider a defensive override only after more falling sequences accumulate and after evaluating duration, avoided loss, and round-trip costs.", "CalloutX"),
        p("Why this is the prudent choice", "H2X"),
        p("The simple Conditional rule has no extra parameter fitted to this small dataset, respects existing replacement controls, and is easy to audit. A defensive override can still be promoted later if forward shadow results show a repeatable net benefit after costs."),
        p("Method and limitations", "H1X"),
        p(f"Source: {len(snapshots)} accepted snapshots and {len(snapshots)-1} measured intervals, including {falling} falling intervals under the ±1% definition. Replays use stored subnet prices and the frozen SRBbot cost model. They assume trades occur at each sample's recorded price after the condition is observed. SN51 was present in every snapshot. Market capitalization, liquidity, execution depth, and intrahour paths are not present in the dataset. The proposed Conditional rule was designed after observing part of this history, so historical replay is in-sample; future observations are required for confirmation.", "SmallX"),
    ]
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=.7*inch, rightMargin=.7*inch, topMargin=.62*inch, bottomMargin=.7*inch, title="SRBbot in falling Tao markets", author="Codex")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.resolve())
    for key in policies:
        x = policies[key]
        print(key, "ending", x["ending"], "return", x["return"], "dd", x["drawdown"], "switches", x["switches"], "costs", x["costs"])
    print("next", next_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.db, args.output)
