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


OUTPUT = Path("output/pdf/9-Codex-final-prelaunch.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
GREEN = colors.HexColor("#217A4B")
AMBER = colors.HexColor("#A85D00")
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
            fontSize=8,
            leading=10.4,
            textColor=color,
        )
    )


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - final prelaunch architecture")
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
    Paragraph("SRBbot: final prelaunch architecture", styles["TitleCustom"]),
    Paragraph(
        "Socket.IO transport, authorization, retained-state recovery, and E2E proof | "
        "10 October 2026",
        styles["Subtitle"],
    ),
    Paragraph(
        "<b>STATUS:</b> The client architecture and local integration test are complete. "
        "The remaining proof is a staging run against the actual Sites SRB server. The live "
        "paper experiment has not been started and still requires explicit authorization.",
        styles["Status"],
    ),
    Paragraph("1 | Sites address and Socket.IO", styles["H1Custom"]),
    Paragraph(
        "Use the same public HTTPS address and port as the Sites server. A reverse proxy "
        "routes ordinary Sites requests to the Sites application and requests on "
        "<font name='Courier'>/socket.io</font> to a loopback-only Socket.IO process.",
        styles["BodyCustom"],
    ),
    Preformatted(
        "https://sites.example/\n"
        "  normal request  -> Sites application\n"
        "  /socket.io      -> internal Socket.IO process",
        styles["CodeCustom"],
    ),
    Paragraph(
        "Socket.IO is not identical to raw WebSocket. It is an event protocol that normally "
        "uses WebSocket after its handshake and can fall back to HTTP polling. SRBbot requests "
        "the WebSocket transport directly.",
        styles["Note"],
    ),
    Paragraph("Named traffic organization", styles["H2Custom"]),
    table(
        [
            ["Mechanism", "Initial SRBbot use", "Future use"],
            ["Namespace", "/srbbot", "Separate protocol or privilege domains"],
            ["Event", "subnets_state_sampled", "Additional named message types on one connection"],
            ["Room", "Not initially required", "Selected clients or authorization groups"],
        ],
        [1.3 * inch, 2.15 * inch, 3.4 * inch],
    ),
    Spacer(1, 8),
    Paragraph(
        "One Socket.IO connection can therefore carry multiple named streams without assigning "
        "a separate TCP port to every type of traffic. An internal port such as 8081 remains "
        "acceptable behind the proxy; it need not be publicly exposed.",
        styles["BodyCustom"],
    ),
    Paragraph("2 | Recommended authorization", styles["H1Custom"]),
    Paragraph(
        "Use a short-lived signed token issued by Sites after normal user authentication. "
        "The provisional staging identity is <b>mark.rudolph@gmail.com</b>, subject to exact "
        "spelling and allowlist confirmation.",
        styles["BodyCustom"],
    ),
    table(
        [
            ["Step", "Responsibility"],
            ["1", "Sites authenticates the user through its existing login mechanism."],
            ["2", "Sites issues a short-lived signed token containing account ID, verified email, issuer, SRB audience, issue time, and expiration."],
            ["3", "SRBbot supplies the bearer token and the configured email during the Socket.IO connection."],
            ["4", "The Socket.IO server verifies signature, issuer, audience, expiration, and verified-email claim."],
            ["5", "The server requires the claim to match auth.email and the SRB allowlist; any failure rejects the connection."],
        ],
        [0.55 * inch, 6.3 * inch],
    ),
    Spacer(1, 8),
    Paragraph(
        "A 15-60 minute renewable staging token is appropriate. Sites should create it; "
        "SRBbot should not mint identity tokens. The email alone is an authorization selector, "
        "not identity proof. Never commit the token or a populated environment file.",
        styles["Caution"],
    ),
    Paragraph("3 | Retained-state recovery contract", styles["H1Custom"]),
    Paragraph(
        "SRB stores the latest complete committed state sample before clients connect. After "
        "every authorized connection or reconnection, it immediately sends that retained "
        "sample. The client applies its normal timestamp and duplicate checks.",
        styles["BodyCustom"],
    ),
    Preformatted(
        "SRB stores current sample\n"
        "        |\n"
        "client connects -> retained sample -> accepted -> one atomic write\n"
        "        |\n"
        "disconnect / reconnect\n"
        "        |\n"
        "retained sample again -> duplicate -> no write",
        styles["CodeCustom"],
    ),
    Paragraph("4 | E2E verification of retained-state recovery", styles["H1Custom"]),
    Paragraph(
        "The strengthened local E2E test now verifies the recovery contract rather than merely "
        "sending the same message twice on one connection.",
        styles["BodyCustom"],
    ),
    bullets(
        [
            "Starts a real local Socket.IO server using WebSocket transport.",
            "Stores the current sample before any authorized client arrives.",
            "Rejects a connection with a non-allowlisted email.",
            "Accepts the authorized email and bearer token.",
            "Sends the retained sample after the first connection and receives an accepted acknowledgement.",
            "Disconnects and reconnects the client, then sends the same retained sample again.",
            "Receives a duplicate acknowledgement and confirms that no second decision cycle was written.",
        ]
    ),
    table(
        [
            ["Verification", "Result"],
            ["Retained-sample reconnect E2E", "Passed"],
            ["Complete automated suite", "14 passed"],
            ["Focused source/test linting", "Passed"],
            ["Persisted cardinality", "1 snapshot, 2 decisions, 2 strategy NAV rows"],
        ],
        [3.05 * inch, 3.8 * inch],
    ),
    Spacer(1, 8),
    Paragraph("5 | Production event contract", styles["H1Custom"]),
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
        "With positive <font name='Courier'>price_tao</font> present for every subnet, the paper "
        "experiment does not require a validator mapping, wallet address, wallet key, or a "
        "separate chain quote adapter. Malformed or incomplete events reject atomically.",
        styles["Note"],
    ),
    Paragraph("6 | Final staging proof", styles["H1Custom"]),
    bullets(
        [
            "Confirm and allowlist the exact test email.",
            "Issue a short-lived staging token from Sites.",
            "Connect through the real Sites HTTPS origin and /socket.io path.",
            "Verify unauthorized rejection and authorized retained-sample delivery.",
            "Reconnect and verify duplicate acknowledgement with no additional writes.",
            "Accept one subsequent unique state sample containing price_tao for every subnet.",
            "Inspect Score and Breakout holdings, fills, NAV, return, and tao-market values.",
            "Run preflight against a fresh database and require zero blockers.",
        ]
    ),
    Paragraph(
        "<b>Final gate:</b> Passing the local E2E test proves the client contract. Passing the "
        "same sequence against the actual SRB staging service proves the server's retention, "
        "reverse proxy, token verification, and payload implementation. Only then, and after "
        "an explicit start instruction, should the persistent listener begin the experiment.",
        styles["Status"],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot final prelaunch architecture",
    author="Codex",
    subject="Final Socket.IO, authorization, retained-state, and staging acceptance design",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
