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


OUTPUT = Path("output/pdf/8-Codex-removing-blockers.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
GREEN = colors.HexColor("#217A4B")
AMBER = colors.HexColor("#A85D00")
RED = colors.HexColor("#9A3412")
PALE_GREEN = colors.HexColor("#EAF6EF")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_AMBER = colors.HexColor("#FFF4E5")
GRAY = colors.HexColor("#556270")
BODY = colors.HexColor("#23313D")
GRID = colors.HexColor("#C9D5DE")

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
        spaceBefore=9,
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
        fontSize=9.25,
        leading=13.3,
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
        fontSize=9.4,
        leading=13.8,
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
        fontSize=7.5,
        leading=10.2,
        textColor=colors.HexColor("#17232D"),
        backColor=colors.HexColor("#F4F6F8"),
        borderColor=GRID,
        borderWidth=0.5,
        borderPadding=8,
        spaceAfter=9,
    )
)
for name, font, color in (
    ("TableHeader", "Helvetica-Bold", colors.white),
    ("TableLabel", "Helvetica-Bold", BODY),
    ("TableCell", "Helvetica", BODY),
):
    styles.add(
        ParagraphStyle(
            name=name,
            parent=styles["BodyText"],
            fontName=font,
            fontSize=7.8,
            leading=10.1,
            textColor=color,
        )
    )


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - removing launch blockers")
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
    Paragraph("SRBbot: removing launch blockers", styles["TitleCustom"]),
    Paragraph(
        "Remaining integration work, ownership, and acceptance tests | 10 October 2026",
        styles["Subtitle"],
    ),
    Paragraph(
        "<b>SUMMARY:</b> The SRBbot client and local persistence path are ready for staging. "
        "The remaining blockers are all production-SRB integration inputs: endpoint routing, "
        "verified authorization, the retained event, and complete per-subnet pricing. None "
        "requires a change to the two strategy rules. Local verification is complete: the "
        "real-WebSocket E2E test and all 14 automated tests pass.",
        styles["Status"],
    ),
    Paragraph("1 | Provisional test identity", styles["H1Custom"]),
    Paragraph(
        "Use <b>mark.rudolph@gmail.com</b> as the provisional staging identity. Before it is "
        "configured, confirm that this is the exact email attached to the Sites SRB account "
        "and that it appears on the server-side allowlist.",
        styles["BodyCustom"],
    ),
    Paragraph(
        "An email sent in a Socket.IO connection request is only an authorization selector. "
        "It is not proof of identity. The connection must also include a signed bearer token; "
        "the server verifies the token, extracts its verified email claim, requires that claim "
        "to match <b>mark.rudolph@gmail.com</b>, and checks the same email against the SRB "
        "allowlist. Do not commit the token or a populated environment file.",
        styles["Caution"],
    ),
    Preformatted(
        "SRBBOT_AUTH_EMAIL=mark.rudolph@gmail.com\n"
        "SRBBOT_SOCKETIO_TOKEN=<short-lived signed staging token>",
        styles["CodeCustom"],
    ),
    Paragraph("2 | Remaining blockers and disposal plan", styles["H1Custom"]),
    table(
        [
            ["Blocker", "Owner", "Preferred solution", "Acceptance evidence"],
            [
                "Production Socket.IO route",
                "SRB / Sites",
                "Use the existing Sites HTTPS origin and port. Reverse-proxy /socket.io to a loopback-only Socket.IO process; /srbbot remains the namespace.",
                "SRBbot completes a WebSocket connection through the public Sites URL with a valid certificate.",
            ],
            [
                "Verified email authorization",
                "SRB / Sites",
                "Allowlist the confirmed test email. Validate a signed token and require its verified email claim to match the auth.email value.",
                "Wrong email or token is rejected; the authorized pair connects successfully.",
            ],
            [
                "Retained current sample",
                "SRB",
                "Persist the latest complete committed sample and emit it after every authorized connect or reconnect.",
                "Fresh client receives one current sample without waiting for the next hourly update.",
            ],
            [
                "Complete event payload",
                "SRB",
                "Include netuid, score, delta_price_1h, and positive price_tao for every subnet, plus timestamp and tao_price_usd.",
                "One sanitized event passes normalization and produces executable paper fills and NAV.",
            ],
            [
                "Production staging exercise",
                "Joint",
                "Run SRBbot against staging, receive the retained sample and one subsequent sample, then deliberately replay one event.",
                "Accepted, accepted, and duplicate ACKs; two unique snapshots; four strategy NAV rows; no duplicate writes.",
            ],
        ],
        [1.18 * inch, 0.72 * inch, 2.85 * inch, 2.1 * inch],
    ),
    Spacer(1, 8),
    Paragraph("3 | Items already removed as blockers", styles["H1Custom"]),
    bullets(
        [
            "<b>Port number:</b> no new public port is required. An adjacent port remains possible, but same-origin routing is simpler and safer.",
            "<b>Validator/hotkey and wallet:</b> deferred for paper staking. Server-supplied price_tao is sufficient; SRBbot holds no wallet keys and signs no transactions.",
            "<b>Initial state:</b> Score and Breakout each start with 100 unstaked TAO. On the first valid sample they independently stake the maximum remaining amount after modeled costs according to their selection rule.",
            "<b>Exactly-once processing:</b> every unique valid sample is one SQLite transaction. Replays return duplicate and create no new snapshot, decision, fill, or NAV record.",
            "<b>Local E2E coverage:</b> a real loopback WebSocket test now covers allowed and denied email, bearer token delivery, retained sample delivery, acknowledgement, replay, and database cardinality.",
        ]
    ),
    Paragraph("4 | Frozen event envelope", styles["H1Custom"]),
    Preformatted(
        '''{
  "snapshot_id": "unique-hourly-id",
  "timestamp": "2026-10-10T18:00:00Z",
  "schema_version": "1",
  "tao_price_usd": "350.25",
  "subnets": [
    {
      "netuid": 1,
      "score": "82.5",
      "delta_price_1h": "0.012",
      "price_tao": "0.0042"
    }
  ]
}''',
        styles["CodeCustom"],
    ),
    Paragraph(
        "SRB should send one coherent, immutable event only after the hourly state is fully "
        "committed. Missing fields, duplicate netuids, non-positive prices, stale samples, "
        "or time reversal reject the entire cycle without partial writes.",
        styles["Note"],
    ),
    Paragraph("5 | Staging acceptance sequence", styles["H1Custom"]),
    table(
        [
            ["Step", "Action", "Pass condition"],
            ["1", "Confirm and allowlist mark.rudolph@gmail.com.", "Identity spelling and account ownership confirmed."],
            ["2", "Issue a short-lived staging bearer token.", "Token claim contains the same verified email."],
            ["3", "Publish Socket.IO through the Sites HTTPS origin.", "WebSocket handshake succeeds on /socket.io and namespace /srbbot."],
            ["4", "Connect with a deliberately incorrect email/token pair.", "Server rejects the connection."],
            ["5", "Connect with the authorized identity.", "Server accepts and immediately sends the retained sample."],
            ["6", "Inspect the event before continued operation.", "Every subnet has score, one-hour delta, and positive price_tao."],
            ["7", "Replay the same sample.", "ACK is duplicate and database counts do not change."],
            ["8", "Send the next unique sample.", "ACK is accepted; both strategy NAV rows and tao-market are stored."],
            ["9", "Run the launch preflight.", "Every check passes against a fresh experiment database."],
            ["10", "Obtain explicit start authorization.", "Only then start the persistent listener."],
        ],
        [0.45 * inch, 3.1 * inch, 3.3 * inch],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot removing launch blockers",
    author="Codex",
    subject="Remaining SRBbot launch blockers, owners, solutions, and acceptance evidence",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
