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


OUTPUT = Path("output/pdf/5-Codex-questions.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_GREEN = colors.HexColor("#EAF6EF")
GREEN = colors.HexColor("#217A4B")
AMBER = colors.HexColor("#A86500")
GRAY = colors.HexColor("#556270")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=NAVY, spaceAfter=10, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=10.5, leading=14, textColor=GRAY, spaceAfter=18))
styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=NAVY, spaceBefore=10, spaceAfter=7))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.3, leading=13.4, textColor=colors.HexColor("#23313D"), spaceAfter=6))
styles.add(ParagraphStyle(name="Decision", parent=styles["BodyText"], fontSize=10, leading=14.5, textColor=NAVY, backColor=PALE_GREEN, borderColor=GREEN, borderWidth=0.8, borderPadding=9, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle(name="Question", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=0.8, borderPadding=9, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle(name="CodeCustom", parent=styles["Code"], fontName="Courier", fontSize=7.4, leading=10.2, textColor=colors.HexColor("#17232D"), backColor=colors.HexColor("#F4F6F8"), borderColor=colors.HexColor("#CBD5DD"), borderWidth=0.5, borderPadding=8, spaceAfter=10))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.5, leading=10, textColor=GRAY))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - decisions and launch questions")
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
    Paragraph("SRBbot: decisions and remaining questions", styles["TitleCustom"]),
    Paragraph("Response to the attempt to freeze the initial specification | 9 October 2026", styles["Subtitle"]),
    Paragraph("<b>AGREEMENT:</b> The strategy specification is substantially agreed. Socket.IO is accepted as the notification transport, the experiment begins with two independent 100 TAO paper portfolios in a fresh database, and Breakout uses the published 1-hour delta as a decimal fraction.", styles["Decision"]),
    Paragraph("1 | Socket.IO event contract", styles["H1Custom"]),
    Paragraph("A single server-to-client event immediately after each accepted hourly subnet sample is a simple and suitable trigger. Socket.IO provides a persistent bidirectional connection, named events, reconnection support, acknowledgements, and optional namespaces or rooms. The event itself can carry the complete decision snapshot, so a second score/delta query is unnecessary.", styles["BodyCustom"]),
    Paragraph("Proposed event", styles["H2Custom"]),
    Table(
        [
            ["Property", "Frozen proposal"],
            ["Namespace", "/srbbot"],
            ["Event name", "subnets_state_sampled"],
            ["Direction", "SRB -> all subscribed SRBbot clients"],
            ["Delivery", "Once, immediately after the hourly sample is committed"],
            ["Identity", "RFC 3339 UTC timestamp; unique and strictly increasing"],
            ["Acknowledgement", "Client ACK containing timestamp and accepted/duplicate/rejected status"],
        ],
        colWidths=[1.35 * inch, 5.5 * inch],
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
    Spacer(1, 9),
    Paragraph("Proposed JSON payload", styles["H2Custom"]),
    Preformatted(
        '''{
  "timestamp": "2026-10-09T20:00:00Z",
  "subnets": [
    {"netuid": 1, "score": 82.5, "delta_price_1h": 0.012},
    {"netuid": 2, "score": 71.0, "delta_price_1h": -0.004}
  ]
}''',
        styles["CodeCustom"],
    ),
    Paragraph("The list-of-objects form is preferred over dynamically named object keys such as <font name='Courier'>\"1\": {...}</font>. It validates cleanly, preserves an explicit integer netuid, and extends naturally if fields are added later. JSON numbers are accepted, but SRBbot must parse their textual representations into Decimal values and never make threshold decisions with binary floating-point arithmetic.", styles["BodyCustom"]),
    Paragraph("Delivery and recovery behavior", styles["H2Custom"]),
    bullets([
        "The SRB must persist the sample before emitting the event; clients must never act on an uncommitted sample.",
        "SRBbot treats the timestamp as the snapshot primary key, acknowledges duplicates without evaluating them again, and rejects time reversal.",
        "Socket.IO delivery is not assumed to be exactly once. On reconnect, the client must request or fetch the latest committed snapshot and process it only if its timestamp is newer. A malformed or incomplete event rejects the entire decision cycle.",
    ]),
    Paragraph("2 | Agreed experiment decisions", styles["H1Custom"]),
    bullets([
        "Two independent virtual portfolios: Score and Breakout, each initialized at exactly 100 TAO.",
        "Breakout values are decimal fractions: 0.01 means 1%. Replacement requires P-new > max(P-held x 1.10, 0.01).",
        "Score replacement requires S-new > S-held x 1.10. Equality results in HOLD for both strategies.",
        "If the held subnet is absent from a new snapshot, reject the complete decision cycle.",
        "Discard disposable 10 TAO records and begin in a fresh SQLite database; do not rewrite historical ledgers.",
        "Use the stable Bittensor package that supplies btcli, pinned to a tested exact version for reproducibility.",
    ]),
    Paragraph("3 | Accounting correction", styles["H1Custom"]),
    Paragraph("Slippage (or price impact) and impermanent loss are different. Slippage is the difference between an indicative price and the executable result of a stake or unstake. Impermanent loss applies to liquidity-provider positions relative to holding the underlying assets. SRBbot is staking, not providing liquidity, so the initial model should set impermanent loss to zero.", styles["Question"]),
    Paragraph("Provisional cost model", styles["H2Custom"]),
    bullets([
        "Apply 0.25% simulated slippage/price impact on each stake and each unstake until executable quotes are integrated.",
        "Record the actual or quoted network fee separately when available; do not hide it inside slippage.",
        "Version these assumptions so later quote-based results never silently rewrite the baseline experiment.",
    ]),
    Paragraph("4 | Two launch-critical questions remain", styles["H1Custom"]),
    Paragraph("<b>Question A - executable valuation:</b> score and 1-hour delta select a subnet, but they do not reveal how much subnet alpha 100 TAO buys or how much TAO an unstake returns. Please confirm whether SRBbot should obtain the current subnet price and liquidity/quote data from btcli immediately after receiving the event, or whether those fields will be added to the SRB event.", styles["Question"]),
    Paragraph("<b>Question B - TAO/USD valuation:</b> the specification requires storing the TAO price in dollars after every cycle. Please identify its source: the SRB event, another SRB endpoint, btcli/chain data if available, or a named external price feed.", styles["Question"]),
    Paragraph("5 | Launch assessment", styles["H1Custom"]),
    Paragraph("<b>Almost ready.</b> The strategy and notification decisions are clear. The first live-fed 100 TAO paper experiment should launch after Questions A and B are answered and one real Socket.IO event is captured as a sanitized fixture. At that point the exact event schema, price source, cost-model version, and Bittensor package version can be frozen and tested end to end.", styles["Decision"]),
    Paragraph("Package note", styles["H2Custom"]),
    Paragraph("As checked on 9 October 2026, the standalone bittensor-cli v9 package is superseded by the Bittensor 11 package, which includes btcli. The then-current stable PyPI release is bittensor 11.3.0. Pinning should occur when the environment is frozen, followed by a compatibility smoke test.", styles["BodyCustom"]),
    Paragraph("References: https://pypi.org/project/bittensor/  |  https://github.com/RaoFoundation/btcli", styles["Small"]),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot decisions and remaining questions",
    author="Codex",
    subject="Socket.IO contract and launch questions for the initial 100 TAO experiment",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
