from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT = Path("output/pdf/5-Codex-initial-spec.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
PALE = colors.HexColor("#EAF3F8")
GREEN = colors.HexColor("#217A4B")
AMBER = colors.HexColor("#A86500")
GRAY = colors.HexColor("#556270")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY, spaceAfter=12, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=11, leading=15, textColor=GRAY, spaceAfter=20))
styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=NAVY, spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BLUE, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=colors.HexColor("#23313D"), spaceAfter=7))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontSize=10, leading=15, textColor=NAVY, backColor=PALE, borderColor=BLUE, borderWidth=0.8, borderPadding=10, spaceBefore=6, spaceAfter=12))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=11, textColor=GRAY))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot initial implementation - Codex review")
    canvas.drawRightString(7.78 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["BodyCustom"]), leftIndent=12) for item in items],
        bulletType="bullet", leftIndent=18, bulletFontName="Helvetica", bulletFontSize=7, spaceAfter=8,
    )


table_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("LEADING", (0, 0), (-1, -1), 12),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D5DE")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
])

story = [
    Paragraph("SRBbot initial specification", styles["TitleCustom"]),
    Paragraph("Implementation comment and clarification note | 9 October 2026", styles["Subtitle"]),
    Paragraph("<b>COMMENT:</b> The specification is suitable for a first simulation-only vertical slice. The implementation should remain deterministic, keep the two strategy ledgers independent, and avoid signing authority. One correction is now authoritative: <b>Breakout uses the published 1-hour price delta, not a 24-hour delta.</b>", styles["Callout"]),
    Paragraph("1 | Agreed behavior", styles["H1Custom"]),
    bullets([
        "All prices and portfolio values are denominated in TAO; scores are constrained to [0, 100].",
        "Score and Breakout each begin with an independent 100 TAO paper portfolio, making a 1 TAO gain or loss initially equal to one percentage point.",
        "On the first accepted hourly snapshot, Score stakes the maximum available amount, after modeled costs, into the highest-scoring subnet.",
        "On the same snapshot, Breakout stakes the maximum available amount, after modeled costs, into the subnet with the highest published 1-hour price delta.",
        "At most one subnet is held by each strategy. The strategies evaluate the same immutable snapshot but make decisions independently.",
    ]),
    Paragraph("Replacement rules", styles["H2Custom"]),
    Table([
        ["Strategy", "Candidate", "Replace only when"],
        ["Score", "Highest current score", "S-new > S-held x 1.10"],
        ["Breakout", "Highest current 1-hour delta", "P-new > max(P-held x 1.10, 0.01)"],
    ], colWidths=[1.0 * inch, 2.35 * inch, 3.5 * inch], repeatRows=1, style=table_style),
    Spacer(1, 10),
    Paragraph("The word <b>greater</b> is interpreted strictly. Equality with either threshold results in HOLD. A lower netuid is used as the deterministic tie-breaker when candidate values are equal.", styles["BodyCustom"]),
    Paragraph("2 | Accounting and evidence", styles["H1Custom"]),
    bullets([
        "Balances use integer rao (1 TAO = 1,000,000,000 rao); decision values use decimal arithmetic.",
        "A replacement first simulates a complete unstake, deducts configured exit costs, then stakes the maximum remaining TAO and deducts configured entry costs.",
        "After every accepted snapshot, SQLite records the held subnet, free balance, alpha units, executable TAO NAV, return percentage from the 100 TAO baseline, TAO/USD price, decisions, and fills.",
        "Duplicate snapshots and time reversal fail closed. Incomplete, invalid, stale, or non-HTTPS live input is rejected before strategy evaluation.",
    ]),
    PageBreak(),
    Paragraph("3 | Implementation status", styles["H1Custom"]),
    Table([
        ["Area", "Status", "Comment"],
        ["Snapshot client", "Implemented", "HTTPS and saved-fixture ingestion; schema and freshness checks."],
        ["Score strategy", "Implemented", "Initial entry, hold, strict 10% replacement."],
        ["Breakout strategy", "Implemented", "Published 1-hour delta and 0.01 minimum threshold."],
        ["Paper broker", "Implemented", "Configurable stake, unstake, and slippage basis points."],
        ["SQLite journal", "Implemented", "Snapshots, observations, portfolios, decisions, fills, NAV, and return percentage."],
        ["Continuous runner", "Implemented", "Restart-safe duplicate suppression and configurable polling."],
        ["Live btcli execution", "Deferred", "No wallet keys or signing authority in this milestone."],
    ], colWidths=[1.35 * inch, 1.05 * inch, 4.45 * inch], repeatRows=1, style=TableStyle(table_style.getCommands() + [
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 1), (1, -2), GREEN),
        ("TEXTCOLOR", (1, -1), (1, -1), AMBER),
    ])),
    Spacer(1, 12),
    Paragraph("4 | Items still requiring confirmation", styles["H1Custom"]),
    bullets([
        "Provide one sanitized real Sites Stage2 SRB response and the production query URL, including authentication requirements if any.",
        "Confirm whether the published 1-hour delta is represented as a decimal fraction (0.01 = 1%) or as percentage points (1.0 = 1%). The threshold must use the same unit.",
        "Select and pin the intended btcli/Bittensor package version before adding any chain-derived quote adapter.",
        "Freeze the initial fee, slippage, and impermanent-loss assumptions. Current values are configurable and default to zero.",
        "Define expected behavior when the currently held subnet disappears from a later accepted snapshot. The current safe behavior is to reject that decision cycle.",
        "Confirm whether the Sites API exposes a stable snapshot ID; otherwise the client uses a stable content hash.",
        "Begin the 100 TAO experiment with a fresh database. Any earlier 10 TAO database remains historical and is rejected rather than silently rewritten.",
    ]),
    Paragraph("5 | Acceptance comment", styles["H1Custom"]),
    Paragraph("The foundation is acceptable for fixture-based paper testing. Automated coverage currently verifies 100 TAO initialization, independent first entries, strict threshold boundaries, fee-bearing replacement, NAV and percentage-return persistence, invalid input rejection, duplicate rejection, and time-order rejection. The remaining gate for a realistic trial is the real Sites response contract and agreed cost assumptions.", styles["Callout"]),
    Paragraph("Recommended next step", styles["H2Custom"]),
    Paragraph("Freeze a sanitized hourly response as a versioned fixture, map its exact field names to the normalizer, then replay several consecutive samples through a fresh SQLite database and compare the resulting holdings and NAV records with hand-calculated expectations.", styles["BodyCustom"]),
]

document = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter, rightMargin=0.72 * inch, leftMargin=0.72 * inch,
    topMargin=0.7 * inch, bottomMargin=0.72 * inch,
    title="SRBbot initial specification - implementation comment", author="Codex",
    subject="Review comments for the SRBbot initial paper-simulation specification",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
