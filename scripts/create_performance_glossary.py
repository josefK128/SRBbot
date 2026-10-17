from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT = Path("output/pdf/SRBbot-performance-report-glossary.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#18324A")
BLUE = colors.HexColor("#2D6F9F")
GRAY = colors.HexColor("#5D6873")
GRID = colors.HexColor("#D4DCE3")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF3DF")
ORANGE = colors.HexColor("#D07A28")
BODY = colors.HexColor("#263440")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5))
styles.add(ParagraphStyle(name="SubtitleX", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=GRAY, spaceAfter=12))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontSize=8.8, leading=12.2, textColor=BODY, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=7.4, leading=9.6, textColor=GRAY))
styles.add(ParagraphStyle(name="HeaderX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=9.6, textColor=colors.white))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontSize=9, leading=12.8, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=.7, borderPadding=8, spaceAfter=9))
styles.add(ParagraphStyle(name="CautionX", parent=styles["BodyText"], fontSize=8.7, leading=12.3, textColor=NAVY, backColor=PALE_AMBER, borderColor=ORANGE, borderWidth=.7, borderPadding=8, spaceBefore=4, spaceAfter=9))


def p(text, style="BodyX"):
    return Paragraph(text, styles[style])


def glossary(rows, widths=(1.65 * inch, 5.25 * inch)):
    data = [[p("Term", "HeaderX"), p("Definition and how to interpret it", "HeaderX")]]
    for term, definition in rows:
        data.append([
            Paragraph(f"<b>{term}</b>", ParagraphStyle(name="Term", parent=styles["BodyX"], fontSize=8.4, leading=11, textColor=BODY)),
            p(definition),
        ])
    return Table(data, colWidths=widths, repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(.7 * inch, .55 * inch, 7.8 * inch, .55 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(.7 * inch, .36 * inch, "SRBbot performance report glossary")
    canvas.drawRightString(7.8 * inch, .36 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = [
    p("SRBbot performance report glossary", "TitleX"),
    p("Definitions for the names and terms used in the tables | Companion to the Oct 13, 2026 current-performance report", "SubtitleX"),
    p("<b>Purpose:</b> This guide explains what each left-column label means, how it is calculated, and what it does - and does not - say about the Score and Breakout simulations.", "CalloutX"),
    p("1 | Essential names and units", "H1X"),
    glossary([
        ("Score", "The strategy that holds the subnet with the highest published score. It replaces its holding only when another subnet's score is more than 110% of the held subnet's current score. Ties favor the lower netuid."),
        ("Breakout", "The strategy that ranks subnets by published one-hour price change. It replaces its holding when the best candidate exceeds both 110% of the held subnet's one-hour change and the fixed 0.01 floor. This rule can trade frequently when leadership changes."),
        ("TAO", "The accounting currency of the simulation. Each strategy started with 100 TAO. Reported NAV, profit/loss, turnover, and costs are stated in TAO, not US dollars."),
        ("Subnet / netuid", "A subnet is the simulated investment target. Its <i>netuid</i> is the numerical identifier used by Bittensor and by SRBbot; for example, netuid 35 means subnet 35."),
        ("Sample", "One accepted, complete hourly SRB snapshot. A sample contains Tao's USD price and the score, one-hour price change, and TAO-denominated price for every subnet."),
        ("Interval", "The period between two consecutive accepted samples. A return or Tao market condition requires two samples, so 49 samples produce 48 measurable intervals."),
    ]),
    Spacer(1, 7),
    p("2 | Experiment coverage table", "H1X"),
    glossary([
        ("Window", "The first and last accepted sample timestamps included in the analysis. It describes the measurement period; it does not imply uninterrupted wall-clock operation unless data completeness is separately verified."),
    ]),
    Spacer(1, 7),
    p("3 | Tao condition table", "H1X"),
    glossary([
        ("Falling (-1)", "The contemporaneous hourly Tao market condition when Tao's USD price fell by more than 1% from the previous accepted sample: change &lt; -1%."),
        ("Static (0)", "The condition when Tao's hourly USD-price change stayed within the inclusive band from -1% through +1%. 'Static' means inside this tolerance band, not literally unchanged."),
        ("Rising (+1)", "The condition when Tao's USD price rose by more than 1% from the previous accepted sample: change &gt; +1%."),
    ]),
    p("The condition describes <b>Tao's USD-price move</b>, not whether a strategy or subnet gained or lost TAO. A strategy can gain during a falling Tao interval or lose during a rising one.", "CautionX"),
    p("4 | Overall performance table", "H1X"),
    glossary([
        ("Ending liquidation NAV", "The strategy's latest total value in TAO after marking the held subnet at its current price and deducting the modeled cost of an immediate unstake. 'Liquidation' answers: what would the position be worth if closed at this sample?"),
        ("Net return from 100 TAO", "Percentage gain or loss relative to the fixed 100 TAO starting balance: (ending NAV / 100 - 1) x 100. A value of +8% means the strategy ended near 108 TAO."),
        ("Net P/L", "Net profit or loss in TAO: ending liquidation NAV minus the 100 TAO start. Positive is profit; negative is loss."),
        ("Maximum drawdown", "The worst peak-to-later-trough percentage decline in the recorded liquidation-NAV path. It measures interim downside and path risk, even when the final return is positive."),
        ("Positive / negative / flat intervals", "Counts of intervals in which liquidation NAV rose, fell, or was unchanged versus the immediately preceding accepted sample. These are directional counts, not the sizes of the moves."),
        ("Replacements (plus initial entry)", "A replacement is a complete switch: unstake the held subnet and stake the selected candidate. The parenthetical initial entry is the first stake from cash and is shown separately because it is not a replacement."),
        ("Executed turnover", "The sum of TAO amounts recorded on all stake and unstake fills. It is a trading-activity measure and can greatly exceed starting capital because the same capital may be traded repeatedly."),
        ("Realized modeled costs", "The sum of fees and modeled price impact actually booked on executed fills, including the fixed network estimate. It excludes the hypothetical current exit cost embedded only in liquidation NAV until that exit is executed."),
        ("Current subnet", "The netuid held by the strategy at the report cutoff. It is a position identifier, not a rank or performance score."),
    ]),
    Spacer(1, 7),
    p("5 | Performance-by-condition tables", "H1X"),
    glossary([
        ("Condition", "The Tao regime assigned to each interval: Falling, Static, or Rising, using the thresholds above."),
        ("Falling / Static / Rising", "The rows group strategy interval returns by the Tao condition on the interval's ending snapshot. They are attribution buckets, not separate portfolios."),
        ("Intervals", "The number of measured intervals in that condition. This is the sample size (<i>n</i>). Very small counts should not be treated as evidence of repeatable behavior."),
        ("Linked return", "The compounded strategy return across only the intervals in that condition: multiply (1 + each interval return), then subtract 1. It preserves compounding but links non-adjacent intervals when a condition recurs."),
        ("P/L contribution", "The arithmetic sum of each selected interval's change in liquidation NAV, stated in TAO. Contributions across the three conditions add to the total NAV change across measured intervals, subject to rounding."),
        ("Mean interval return", "The simple arithmetic average of strategy percentage returns for intervals in that condition. It describes the average one-interval move and is not the same as compounded return."),
        ("Positive-interval rate", "The percentage of intervals in that condition with a strategy return above zero: positive intervals / total intervals x 100. It measures frequency, not payoff size."),
        ("Interval volatility", "The population standard deviation of interval percentage returns within that condition. Higher values mean returns varied more from interval to interval. It is not annualized, and it is not reported for a one-interval sample."),
        ("Evidence rating", "A qualitative warning based on sample count. In the report, fewer than 5 intervals is 'insufficient for inference,' 5-19 is 'still preliminary,' and 20 or more is 'directionally informative.' It is not a formal statistical-confidence test."),
    ]),
    p("6 | Reading the measures together", "H1X"),
    p("Return answers <i>how much</i>; drawdown and volatility describe <i>how unevenly</i>; positive-interval rate describes <i>how often</i>; replacements, turnover, and realized costs describe <i>how actively and expensively</i>. No single measure establishes that a strategy is superior.", "CalloutX"),
    p("The current report is a short simulation, not live trading. Results include the frozen modeled costs and observed SRB inputs, but they do not establish future performance, execution quality, or statistical significance.", "CautionX"),
]

doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=.7*inch, rightMargin=.7*inch, topMargin=.62*inch, bottomMargin=.7*inch, title="SRBbot performance report glossary", author="Codex", subject="Definitions for terms used in the SRBbot performance tables")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
