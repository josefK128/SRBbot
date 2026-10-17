from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT = Path("output/pdf/6-Codex-freeze-spec-before-launch.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
GREEN = colors.HexColor("#217A4B")
PALE_GREEN = colors.HexColor("#EAF6EF")
PALE_BLUE = colors.HexColor("#EAF3F8")
GRAY = colors.HexColor("#556270")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=NAVY, spaceAfter=10, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=10.5, leading=14, textColor=GRAY, spaceAfter=17))
styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=NAVY, spaceBefore=9, spaceAfter=7))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.3, leading=13.4, textColor=colors.HexColor("#23313D"), spaceAfter=6))
styles.add(ParagraphStyle(name="Frozen", parent=styles["BodyText"], fontSize=10, leading=14.5, textColor=NAVY, backColor=PALE_GREEN, borderColor=GREEN, borderWidth=0.8, borderPadding=9, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=0.8, borderPadding=9, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle(name="CodeCustom", parent=styles["Code"], fontName="Courier", fontSize=7.4, leading=10.2, textColor=colors.HexColor("#17232D"), backColor=colors.HexColor("#F4F6F8"), borderColor=colors.HexColor("#CBD5DD"), borderWidth=0.5, borderPadding=8, spaceAfter=9))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.5, leading=10, textColor=GRAY))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - frozen specification before launch")
    canvas.drawRightString(7.78 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["BodyCustom"]), leftIndent=12) for item in items],
        bulletType="bullet",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=7,
        spaceAfter=7,
    )


story = [
    Paragraph("SRBbot: frozen specification before launch", styles["TitleCustom"]),
    Paragraph("Initial 100 TAO paper experiment | Frozen 9 October 2026", styles["Subtitle"]),
    Paragraph("<b>STATUS: SPECIFICATION FROZEN; EXPERIMENT NOT STARTED.</b> The strategy, notification, accounting, fee, valuation, and database decisions below are agreed. Starting the experiment remains a separate explicit decision.", styles["Frozen"]),
    Paragraph("1 | Experiment and strategy rules", styles["H1Custom"]),
    bullets([
        "Run two independent paper portfolios named Score and Breakout. Each begins with exactly 100 TAO in a fresh SQLite database.",
        "At the first accepted hourly snapshot, Score stakes the maximum available TAO into the highest-scoring subnet. Breakout stakes the maximum available TAO into the subnet with the highest published 1-hour price delta.",
        "Score replaces its held subnet only when S-new > S-held x 1.10.",
        "Breakout uses decimal fractions, where 0.01 means 1%, and replaces only when P-new > max(P-held x 1.10, 0.01).",
        "Equality results in HOLD. Deterministic ties select the lower netuid.",
        "If the held subnet is absent from an accepted snapshot, reject the entire decision cycle with no partial writes.",
        "Discard disposable 10 TAO records. Do not rewrite them into the 100 TAO experiment.",
    ]),
    Paragraph("2 | Socket.IO snapshot delivery", styles["H1Custom"]),
    Paragraph("SRB emits one named Socket.IO event immediately after committing each hourly subnet state sample. The event is the complete immutable decision snapshot; a second score/delta query is unnecessary.", styles["BodyCustom"]),
    Table(
        [
            ["Property", "Frozen value"],
            ["Namespace", "/srbbot"],
            ["Event", "subnets_state_sampled"],
            ["Timestamp", "Unique, strictly increasing RFC 3339 UTC value"],
            ["Delivery", "After the hourly sample is committed"],
            ["ACK", "timestamp plus accepted, duplicate, or rejected status"],
            ["Reconnect", "Fetch/request latest committed snapshot; process only if newer"],
        ],
        colWidths=[1.3 * inch, 5.55 * inch],
        repeatRows=1,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.3),
            ("LEADING", (0, 0), (-1, -1), 11),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D5DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    ),
    Spacer(1, 8),
    Paragraph("Frozen event payload", styles["H2Custom"]),
    Preformatted(
        '''{
  "timestamp": "2026-10-09T20:00:00Z",
  "tao_price_usd": 350.25,
  "subnets": [
    {"netuid": 1, "score": 82.5, "delta_price_1h": 0.012},
    {"netuid": 2, "score": 71.0, "delta_price_1h": -0.004}
  ]
}''',
        styles["CodeCustom"],
    ),
    Paragraph("JSON numbers are parsed into Decimal values before comparisons or accounting. The timestamp is the snapshot primary key. Duplicate timestamps are acknowledged but not evaluated again; time reversal and malformed or incomplete events reject the entire decision cycle.", styles["BodyCustom"]),
    Paragraph("3 | Fees, price impact, and valuation", styles["H1Custom"]),
    Paragraph("Slippage/price impact and impermanent loss are distinct. SRBbot is staking rather than providing liquidity, so modeled impermanent loss is zero. Fees and price impact are recorded separately.", styles["Note"]),
    Table(
        [
            ["Cost", "Frozen provisional model", "100 TAO illustration"],
            ["Application swap fee", "0.05% of transacted amount", "0.0500 TAO"],
            ["Blockchain transaction fee", "0.0001 TAO per operation", "0.0001 TAO"],
            ["Slippage / price impact", "0.25% of transacted amount", "0.2500 TAO"],
            ["Total initial stake reduction", "Sum of the above", "0.3001 TAO"],
            ["Initial executable stake", "100 TAO less modeled costs", "99.6999 TAO"],
        ],
        colWidths=[1.7 * inch, 3.25 * inch, 1.9 * inch],
        repeatRows=1,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, -2), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.1),
            ("LEADING", (0, 0), (-1, -1), 10.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D5DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    ),
    Spacer(1, 8),
    Paragraph("For unstaking, percentage costs apply to gross executable TAO proceeds, not the original 100 TAO. The provisional model is immutable and versioned. Later quote-based accounting creates a new cost-model version rather than rewriting baseline results.", styles["BodyCustom"]),
    Paragraph("4 | MAX replacement sequence", styles["H1Custom"]),
    bullets([
        "Obtain an executable quote for the held alpha position using the pinned Bittensor SDK/btcli dry-run or swap-simulation interface.",
        "Unstake all held alpha to obtain maximum gross TAO proceeds.",
        "Deduct the estimated unstake swap fee, blockchain fee, and price impact.",
        "Obtain an executable stake quote for the selected destination subnet.",
        "Stake the maximum remaining free TAO after reserving/deducting the stake operation costs.",
        "Leave only an indivisible rounding remainder. Record both fills, all costs, and post-cycle executable NAV.",
    ]),
    Paragraph("This MAX policy is intentionally radical. It fully stresses quote handling, fee accounting, price impact, and TAO-equivalent valuation while retaining the K=1 strategy design.", styles["BodyCustom"]),
    Paragraph("5 | Persistence and launch gate", styles["H1Custom"]),
    bullets([
        "After every accepted snapshot, persist each strategy's held subnet, free TAO, alpha units, executable NAV in TAO, percentage return from 100 TAO, TAO/USD price, decisions, fills, and costs.",
        "Pin the tested stable Bittensor package version that supplies btcli. At specification freeze, the stable release was bittensor 11.3.0.",
        "Capture one real sanitized Socket.IO event and validate it end to end before starting the hourly experiment.",
    ]),
    Paragraph("<b>Launch decision:</b> the specification is ready. The experiment has not been started. Beginning tonight or tomorrow morning requires a separate explicit instruction after fixture validation.", styles["Frozen"]),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot frozen specification before launch",
    author="Codex",
    subject="Frozen initial specification for the 100 TAO paper experiment",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
