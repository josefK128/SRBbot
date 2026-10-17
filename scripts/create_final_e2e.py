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


OUTPUT = Path("output/pdf/10-Codex-final-E2E.pdf")
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
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - final staging E2E plan")
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
    Paragraph("SRBbot: final staging E2E plan", styles["TitleCustom"]),
    Paragraph(
        "One bounded test for the remaining confirmations | 10 October 2026",
        styles["Subtitle"],
    ),
    Paragraph(
        "<b>CONCLUSION:</b> Confirmations 1-7 can be verified in one controlled staging "
        "end-to-end test. Confirmation 8 is the test's final report and clean shutdown. "
        "The test must not start or leave running the persistent production listener.",
        styles["Status"],
    ),
    Paragraph("1 | The eight-step staging test", styles["H1Custom"]),
    table(
        [
            ["Step", "Test action", "Required result"],
            ["1", "Run the non-connecting preflight against a fresh temporary database.", "Configuration is complete; no connection is made yet."],
            ["2", "Connect with a deliberately unauthorized email or token.", "The SRB Socket.IO server rejects the connection."],
            ["3", "Connect with the allowlisted email and short-lived signed token.", "The authenticated WebSocket and /srbbot namespace connect."],
            ["4", "Receive the server's retained current state sample.", "Client validates it, commits one atomic decision cycle, and ACKs accepted."],
            ["5", "Disconnect and reconnect using the authorized identity.", "Server sends the retained sample again; client ACKs duplicate and writes nothing."],
            ["6", "Advance staging to a second unique valid sample.", "Client ACKs accepted and commits one additional decision cycle."],
            ["7", "Inspect persisted strategy results and cardinality.", "Exactly 2 snapshots, 4 decisions and 4 NAV rows; Score, Breakout, fills, fees, returns, and tao-market are valid."],
            ["8", "Write the test report, close Socket.IO, terminate the harness, and inspect the report.", "No persistent listener remains running. Starting the experiment still requires a separate instruction."],
        ],
        [0.45 * inch, 3.15 * inch, 3.25 * inch],
    ),
    Spacer(1, 8),
    Paragraph(
        "The automated checks can validate schema, counts, calculations, acknowledgements, "
        "and shutdown. The final human inspection reviews the generated evidence. It does not "
        "implicitly authorize the live experiment.",
        styles["Note"],
    ),
    Paragraph("2 | Inputs required to implement and run it", styles["H1Custom"]),
    bullets(
        [
            "The exact staging Sites HTTPS origin, for example <font name='Courier'>https://staging.example.com</font>.",
            "Confirmation that the Engine.IO path is <font name='Courier'>/socket.io</font>, namespace is <font name='Courier'>/srbbot</font>, and event is <font name='Courier'>subnets_state_sampled</font>.",
            "Confirmation that <b>mark.rudolph@gmail.com</b> is the exact Sites identity and is present on the staging SRB allowlist.",
            "A short-lived staging bearer token containing the same verified email claim. Set it locally as <font name='Courier'>SRBBOT_SOCKETIO_TOKEN</font>; do not paste it into chat or commit it.",
            "Permission to make several staging connections, including one intentionally unauthorized attempt.",
            "A retained complete state sample containing snapshot ID, timestamp, TAO/USD price, and every subnet's netuid, score, one-hour delta, and positive price_tao.",
            "A deterministic staging-only mechanism that advances the server from retained fixture A to unique fixture B.",
        ]
    ),
    Paragraph("3 | Safe deterministic sample advancement", styles["H1Custom"]),
    Paragraph(
        "Waiting for the next hourly production sample would make the test slow and timing "
        "dependent. The preferred design is a staging-only control that loads two sanitized "
        "fixtures while exercising the normal publication path.",
        styles["BodyCustom"],
    ),
    Preformatted(
        "fixture A stored as retained current sample\n"
        "        |\n"
        "connect -> A accepted\n"
        "        |\n"
        "reconnect -> A duplicate\n"
        "        |\n"
        "authenticated staging control advances to fixture B\n"
        "        |\n"
        "B published normally -> accepted",
        styles["CodeCustom"],
    ),
    Paragraph(
        "The fixture-advance control must require staging administrator authorization, must "
        "operate only in the staging environment, and must be absent or disabled in production.",
        styles["Caution"],
    ),
    Paragraph("Possible control mechanisms", styles["H2Custom"]),
    table(
        [
            ["Option", "Assessment"],
            ["Authenticated staging event", "Fast and natural for Socket.IO, but must be strictly unavailable to ordinary clients."],
            ["Authenticated admin HTTP endpoint", "Clear operational boundary and straightforward automation; recommended."],
            ["Manual server action", "Acceptable for the first run, but less repeatable and harder to diagnose."],
            ["Wait for next hourly sample", "No test-only surface, but slow, timing-dependent, and unsuitable for routine regression testing."],
        ],
        [2.15 * inch, 4.7 * inch],
    ),
    Spacer(1, 8),
    Paragraph("4 | What is already implemented", styles["H1Custom"]),
    bullets(
        [
            "A real local Socket.IO server and WebSocket client connection.",
            "Rejected-email and authorized-email cases with bearer-token delivery.",
            "A retained sample stored before the client connects.",
            "Disconnect, reconnect, and duplicate replay handling.",
            "Accepted and duplicate acknowledgements.",
            "Exactly-once SQLite persistence and controlled test shutdown.",
        ]
    ),
    Paragraph(
        "<b>Verified locally:</b> the retained-sample reconnect E2E test passes; the complete "
        "suite reports 14 passed; focused linting passes.",
        styles["Status"],
    ),
    Paragraph("5 | Final decision required", styles["H1Custom"]),
    Paragraph(
        "The production-staging harness can reuse the existing local test structure and replace "
        "the fake server with the actual Sites SRB endpoint. The remaining design choice is how "
        "staging advances from retained fixture A to unique fixture B. The recommended choice is "
        "an authenticated staging-only admin HTTP endpoint.",
        styles["BodyCustom"],
    ),
    Spacer(1, 7),
    Paragraph(
        "Once the staging URL, exact identity, token workflow, retained fixture, and fixture-advance "
        "mechanism are supplied, the test can be implemented and run without starting the live "
        "paper experiment.",
        styles["Note"],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot final staging E2E plan",
    author="Codex",
    subject="One bounded staging E2E test for the remaining launch confirmations",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
