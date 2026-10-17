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


OUTPUT = Path("output/pdf/11-Codex-launch.pdf")
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
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot - launch path")
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
    Paragraph("SRBbot: launch path", styles["TitleCustom"]),
    Paragraph(
        "Stage2 Socket.IO publication, staging proof, and one-week paper test | "
        "10 October 2026",
        styles["Subtitle"],
    ),
    Paragraph(
        "<b>STATUS:</b> The design questions are resolved. Remaining work is implementation "
        "on the SRB server and one production-staging E2E proof. The real paper experiment "
        "has not started and still requires a separate explicit authorization.",
        styles["Status"],
    ),
    Paragraph("1 | Stage2 origin", styles["H1Custom"]),
    Paragraph(
        "Use the existing Sites Stage2 HTTPS origin as the Socket.IO base URL:",
        styles["BodyCustom"],
    ),
    Preformatted(
        "https://stake-rebalance-stage2.mark-rudolph.chatgpt.site",
        styles["CodeCustom"],
    ),
    Paragraph(
        "A read-only check reached this origin and received HTTP 401 Unauthorized. That is "
        "consistent with an authentication-protected Stage2 service. It confirms that the "
        "public HTTPS origin exists, but it does not yet prove that /socket.io is mounted or "
        "accepts WebSocket upgrades.",
        styles["Note"],
    ),
    Paragraph("2 | Final server behavior", styles["H1Custom"]),
    Paragraph("After every successful hourly state save:", styles["H2Custom"]),
    Preformatted(
        "commit complete subnet state sample\n"
        "        |\n"
        "atomically replace latest retained sample\n"
        "        |\n"
        "broadcast the committed sample to all authorized connected SRBbots",
        styles["CodeCustom"],
    ),
    Paragraph("After every authorized connection or reconnection:", styles["H2Custom"]),
    Preformatted(
        "authorize client\n"
        "        |\n"
        "read latest committed sample\n"
        "        |\n"
        "send it to that client",
        styles["CodeCustom"],
    ),
    Paragraph(
        "This is at-least-once network delivery combined with exactly-once local processing. "
        "A replay is safe because SRBbot identifies the duplicate and performs no additional "
        "database write.",
        styles["BodyCustom"],
    ),
    table(
        [
            ["Socket.IO mechanism", "Use"],
            ["Path", "/socket.io on the existing Stage2 HTTPS origin"],
            ["Namespace", "/srbbot"],
            ["Event", "subnets_state_sampled"],
            ["Per-client delivery", "Send the retained sample to each newly authorized socket"],
            ["Broadcast", "Send every newly committed sample to all authorized connected bots"],
            ["Rooms", "Optional later if different authorized groups need different streams"],
        ],
        [1.7 * inch, 5.15 * inch],
    ),
    Spacer(1, 8),
    Paragraph("3 | Admin endpoint decision", styles["H1Custom"]),
    Paragraph(
        "A staging-only administrative endpoint is not required for the initial launch test. "
        "Its only purpose was to advance immediately from fixture A to fixture B. More than 36 "
        "consecutive successful hourly-save emails make it practical to wait for the next real "
        "hourly sample instead.",
        styles["BodyCustom"],
    ),
    table(
        [
            ["E2E phase", "Expected behavior"],
            ["Initial connection", "Receive retained sample A; ACK accepted"],
            ["Reconnect", "Receive retained sample A again; ACK duplicate; no write"],
            ["Remain connected", "Wait for the next successful hourly commit"],
            ["Next hourly commit", "Receive unique sample B; ACK accepted"],
            ["Inspection", "Verify two snapshots, four decisions, four NAV rows, fills, fees, returns, and tao-market"],
            ["Shutdown", "Close test connection and stop harness; persistent listener remains off"],
        ],
        [1.8 * inch, 5.05 * inch],
    ),
    Spacer(1, 8),
    Paragraph(
        "The test may take slightly more than one hour, but it avoids adding a privileged "
        "test-only surface. An authenticated admin endpoint can still be added later if frequent "
        "deterministic regression runs become necessary.",
        styles["Caution"],
    ),
    Paragraph("4 | Remaining implementation and staging proof", styles["H1Custom"]),
    bullets(
        [
            "Mount a maintained Socket.IO implementation at /socket.io on the supplied Stage2 origin.",
            "Implement namespace /srbbot and event subnets_state_sampled.",
            "Issue and validate a short-lived token for the allowlisted email.",
            "Store the latest complete committed sample and send it after every authorized connection.",
            "Broadcast each sample only after the database save succeeds.",
            "Include positive price_tao for every subnet in every published sample.",
            "Run the real staging E2E and inspect its evidence before authorizing the experiment.",
        ]
    ),
    Paragraph(
        "The hourly success emails support confidence in the state-save job, but do not prove "
        "the event schema, WebSocket publication, reconnect replay, or multi-client delivery. "
        "Those are the purpose of the staging E2E.",
        styles["Note"],
    ),
    Paragraph("5 | One-week real paper-strategy test", styles["H1Custom"]),
    Paragraph(
        "After the staging E2E passes and explicit start authorization is given, run Score and "
        "Breakout continuously for approximately one week.",
        styles["BodyCustom"],
    ),
    Paragraph("Freeze before starting", styles["H2Custom"]),
    bullets(
        [
            "Strategy code, thresholds, and tie-breaking behavior.",
            "Initial 100 TAO balances and modeled cost assumptions.",
            "Event schema, Socket.IO route, and authentication configuration.",
            "Fresh database path plus exact start and end timestamps.",
        ]
    ),
    Paragraph("Monitor without altering strategy behavior", styles["H2Custom"]),
    bullets(
        [
            "Accepted, duplicate, and rejected sample counts; missing hourly periods.",
            "Reconnects, downtime, Score and Breakout NAV, fills, and modeled costs.",
            "TAO market-condition distribution and database integrity.",
        ]
    ),
    Paragraph("Evaluate after approximately one week", styles["H2Custom"]),
    bullets(
        [
            "Total and percentage return, maximum drawdown, turnover, and costs.",
            "Performance in rising, static, and falling TAO markets.",
            "Relative performance of Score and Breakout.",
            "Data completeness and operational reliability.",
        ]
    ),
    Paragraph(
        "dome-vr6 work may continue in parallel provided it does not modify the frozen running "
        "SRBbot code, experiment database, or Stage2 event contract during the test.",
        styles["Caution"],
    ),
    Paragraph("6 | Final sequence", styles["H1Custom"]),
    Preformatted(
        "implement Stage2 Socket.IO publication and authorization\n"
        "                         |\n"
        "run one-hour-plus production-staging E2E\n"
        "                         |\n"
        "inspect and approve evidence\n"
        "                         |\n"
        "explicitly authorize real paper test\n"
        "                         |\n"
        "run approximately one week\n"
        "                         |\n"
        "evaluate strategy and operational results",
        styles["CodeCustom"],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.68 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot launch path",
    author="Codex",
    subject="Stage2 integration, staging E2E, and one-week paper strategy evaluation",
)
document.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
