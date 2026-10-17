from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT = Path("output/pdf/7-Codex-launch-ready.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
GREEN = colors.HexColor("#217A4B")
AMBER = colors.HexColor("#A85D00")
PALE_GREEN = colors.HexColor("#EAF6EF")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF4E5")
GRAY = colors.HexColor("#556270")
GRID = colors.HexColor("#C9D5DE")
BODY = colors.HexColor("#23313D")

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=27,
        textColor=NAVY,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=14,
        textColor=GRAY,
        spaceAfter=16,
    )
)
styles.add(
    ParagraphStyle(
        name="H1Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=7,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="H2Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=BLUE,
        spaceBefore=7,
        spaceAfter=4,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCustom",
        parent=styles["BodyText"],
        fontSize=9.3,
        leading=13.4,
        textColor=BODY,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Status",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14.5,
        textColor=NAVY,
        backColor=PALE_GREEN,
        borderColor=GREEN,
        borderWidth=0.8,
        borderPadding=9,
        spaceBefore=4,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="Caution",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=NAVY,
        backColor=PALE_AMBER,
        borderColor=AMBER,
        borderWidth=0.8,
        borderPadding=9,
        spaceBefore=5,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="Note",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=NAVY,
        backColor=PALE_BLUE,
        borderColor=BLUE,
        borderWidth=0.8,
        borderPadding=9,
        spaceBefore=5,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeCustom",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.7,
        leading=10.5,
        textColor=colors.HexColor("#17232D"),
        backColor=colors.HexColor("#F4F6F8"),
        borderColor=GRID,
        borderWidth=0.5,
        borderPadding=8,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=7.5,
        leading=10,
        textColor=GRAY,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8.1,
        leading=10.6,
        textColor=colors.white,
    )
)
styles.add(
    ParagraphStyle(
        name="TableLabel",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8.1,
        leading=10.6,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        parent=styles["BodyText"],
        fontSize=8.1,
        leading=10.6,
    )
)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - launch readiness review")
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


def table(data, widths):
    formatted = []
    for row_number, row in enumerate(data):
        formatted.append(
            [
                Paragraph(
                    str(value),
                    styles[
                        "TableHeader"
                        if row_number == 0
                        else "TableLabel"
                        if column_number == 0
                        else "TableCell"
                    ],
                )
                for column_number, value in enumerate(row)
            ]
        )
    return Table(
        formatted,
        colWidths=widths,
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )


story = [
    Paragraph("SRBbot: launch readiness review", styles["TitleCustom"]),
    Paragraph(
        "TAO market regime, Socket.IO integration, NAV accounting, and launch gate | "
        "10 October 2026",
        styles["Subtitle"],
    ),
    Paragraph(
        "<b>STATUS: IMPLEMENTATION READY FOR REAL-EVENT VALIDATION; LIVE EXPERIMENT "
        "NOT STARTED.</b> The TAO market-condition enhancement is implemented and tested. "
        "The remaining blockers concern the production data source, authentication, and "
        "executable subnet quote enrichment.",
        styles["Status"],
    ),
    Paragraph("1 | What was reviewed", styles["H1Custom"]),
    Paragraph(
        "Three dome-vr5 reference files were supplied: an older Node Socket.IO server "
        "(<font name='Courier'>index.js</font>), a TypeScript client mediator "
        "(<font name='Courier'>mediator.ts</font>), and a bundled browser client "
        "(<font name='Courier'>socket.io.js</font>). The mediator contains a stale "
        "dome-vr4 comment, but the files are understood to originate from dome-vr5.",
        styles["BodyCustom"],
    ),
    Paragraph(
        "These files were used as transport references only. No dome-vr5 source file was "
        "modified. SRBbot already contains a newer Python Socket.IO listener with its own "
        "frozen namespace and event contract.",
        styles["Note"],
    ),
    Paragraph("2 | TAO market-condition enhancement", styles["H1Custom"]),
    Paragraph(
        "For each accepted snapshot after the first, SRBbot retains the previous TAO/USD "
        "price and calculates the decimal fractional change using exact Decimal arithmetic:",
        styles["BodyCustom"],
    ),
    Preformatted(
        "P = (current_tao_price_usd - previous_tao_price_usd)\n"
        "    / previous_tao_price_usd",
        styles["CodeCustom"],
    ),
    table(
        [
            ["Condition", "tao-market", "Meaning"],
            ["P < -0.02", "-1", "Falling"],
            ["-0.02 <= P <= 0.02", "0", "Static"],
            ["P > 0.02", "1", "Rising"],
            ["No previous sample", "null", "Unknown / not yet classifiable"],
        ],
        [2.15 * inch, 1.15 * inch, 3.55 * inch],
    ),
    Spacer(1, 8),
    Paragraph(
        "The inclusive boundary behavior is deliberate: changes of exactly +2% or -2% "
        "are static. The first accepted sample is <font name='Courier'>null</font>, rather "
        "than 0, because labeling it static would create a false observation and bias "
        "market-conditioned strategy metrics.",
        styles["BodyCustom"],
    ),
    Paragraph("Persistence and reporting", styles["H2Custom"]),
    bullets(
        [
            "The snapshot stores current TAO price, previous TAO price, the exact fractional change, and the -1/0/1 market marker.",
            "The same values are copied onto both Score and Breakout NAV rows, allowing later performance reports to group results by contemporaneous market regime.",
            "Accepted Socket.IO acknowledgements include the JSON property <font name='Courier'>tao-market</font>.",
            "TAO/USD input must be positive; invalid values fail before strategy evaluation.",
            "Existing SQLite databases receive backward-compatible nullable columns automatically.",
        ]
    ),
    Paragraph("Accepted acknowledgement example", styles["H2Custom"]),
    Preformatted(
        '''{
  "timestamp": "2026-10-10T18:00:00Z",
  "status": "accepted",
  "tao-market": 1
}''',
        styles["CodeCustom"],
    ),
    Paragraph("3 | What NAV means", styles["H1Custom"]),
    Paragraph(
        "<b>NAV</b> means <b>Net Asset Value</b>: the current total value of a strategy's "
        "paper portfolio. It includes both uninvested TAO and the estimated executable TAO "
        "proceeds from unstaking the held subnet position.",
        styles["BodyCustom"],
    ),
    Preformatted(
        "NAV = free TAO + estimated TAO received by unstaking the held position",
        styles["CodeCustom"],
    ),
    table(
        [
            ["Example component", "Value"],
            ["Free, uninvested balance", "3 TAO"],
            ["Estimated executable unstake proceeds", "104 TAO"],
            ["Portfolio NAV", "107 TAO"],
        ],
        [4.7 * inch, 2.15 * inch],
    ),
    Spacer(1, 8),
    bullets(
        [
            "<font name='Courier'>nav_rao</font>: NAV in rao, where 1 TAO equals 1,000,000,000 rao.",
            "<font name='Courier'>nav_usd</font>: NAV converted using the current TAO/USD price.",
            "<font name='Courier'>return_percent</font>: gain or loss relative to the strategy's initial 100 TAO.",
        ]
    ),
    Paragraph(
        "NAV is the useful performance measure because most portfolio value is normally "
        "staked; the free wallet balance alone would omit the held position.",
        styles["Note"],
    ),
    Paragraph("4 | Socket.IO integration decision", styles["H1Custom"]),
    Paragraph(
        "The dome-vr5 example server is not wire-compatible with the SRBbot launch contract "
        "as supplied. It uses plain HTTP, the default namespace, and only the "
        "<font name='Courier'>actions</font> and <font name='Courier'>log</font> events. "
        "SRBbot expects the namespace <font name='Courier'>/srbbot</font> and event "
        "<font name='Courier'>subnets_state_sampled</font> over HTTPS.",
        styles["BodyCustom"],
    ),
    table(
        [
            ["Area", "dome-vr5 reference", "SRBbot launch requirement"],
            ["Transport", "Plain HTTP Socket.IO", "HTTPS / WSS"],
            ["Namespace", "Default", "/srbbot"],
            ["Events", "actions, log", "subnets_state_sampled"],
            ["Authentication", "None shown", "Bearer token or explicit unauthenticated decision"],
            ["Recovery", "No latest-snapshot replay", "Retrieve latest committed snapshot after reconnect"],
            ["Payload", "Queued actions", "Atomic subnet snapshot with prices"],
        ],
        [1.25 * inch, 2.25 * inch, 3.35 * inch],
    ),
    Spacer(1, 8),
    Paragraph("Port and TLS", styles["H2Custom"]),
    Paragraph(
        "Port 8081 is reasonable for a loopback-only Node process behind a reverse proxy. "
        "Changing that internal port does not itself improve security. The public production "
        "endpoint should normally use standard HTTPS port 443, with TLS terminated at the "
        "application server or reverse proxy.",
        styles["BodyCustom"],
    ),
    Paragraph("Use maintained implementations", styles["H2Custom"]),
    Paragraph(
        "The bundled Socket.IO 4.5.4 browser file is historical reference material and "
        "must not become a launch dependency. Install maintained JavaScript Socket.IO 4.x "
        "server/client packages through the package manager and pin the exact versions "
        "validated in staging. SRBbot uses python-socketio 5.x; the JavaScript 3.x/4.x and "
        "python-socketio 5.x lines share compatible Socket.IO and Engine.IO protocol revisions.",
        styles["BodyCustom"],
    ),
    Paragraph("5 | Verification completed", styles["H1Custom"]),
    bullets(
        [
            "All 13 automated tests pass, including first-sample null handling, exact +/-2% boundaries, falling-market classification, and persistence on both strategy rows.",
            "Focused linting of application source and tests passes.",
            "The full-repository linter still reports pre-existing formatting issues in older PDF-generation scripts; these do not affect SRBbot runtime behavior.",
            "The non-connecting launch preflight was run and correctly refused to start while required production inputs remain absent.",
        ]
    ),
    Paragraph("6 | Remaining launch blockers", styles["H1Custom"]),
    Paragraph(
        "The implementation is ready for integration testing, but the experiment should not "
        "be started until every item below is supplied and validated end to end.",
        styles["Caution"],
    ),
    table(
        [
            ["Required item", "Why it is needed"],
            ["Production Socket.IO HTTPS URL", "Identifies the real SRB event endpoint."],
            ["Authentication decision", "Provide a bearer token, or explicitly confirm that the endpoint is intentionally unauthenticated."],
            ["One sanitized real event", "Confirms actual field names, units, timestamps, namespace, event name, and acknowledgements."],
            ["price_tao for every subnet", "Score and delta can select a subnet, but executable paper fills and NAV require a subnet price."],
            ["Validator/hotkey target mapping", "A concrete staking target is required for quote enrichment."],
            ["Reconnect/recovery mechanism", "The client must recover the latest committed snapshot without double processing."],
            ["Staging compatibility check", "Validates current Socket.IO packages, TLS, authentication, payload schema, and ACK behavior together."],
        ],
        [2.25 * inch, 4.6 * inch],
    ),
    Spacer(1, 9),
    KeepTogether(
        [
            Paragraph("Recommended next step", styles["H2Custom"]),
            Spacer(1, 5),
            Paragraph(
                "Provide a sanitized production event plus the endpoint and authentication "
                "details. Replay several consecutive events into a fresh SQLite database, "
                "compare the resulting Score and Breakout holdings, fills, NAV, and "
                "tao-market values with hand calculations, then run the complete launch "
                "preflight. Starting the persistent listener remains a separate explicit "
                "authorization.",
                styles["Status"],
            ),
        ]
    ),
    Paragraph(
        "<b>References:</b> Socket.IO 4.x documentation: https://socket.io/docs/v4/ | "
        "python-socketio compatibility: "
        "https://python-socketio.readthedocs.io/en/stable/intro.html<br/>"
        "Local SRBbot contract: docs/snapshot-contract.md | "
        "Local launch gate: docs/launch-checklist.md",
        styles["Small"],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot launch readiness review",
    author="Codex",
    subject="TAO market regime, Socket.IO integration, NAV accounting, and launch gate",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
