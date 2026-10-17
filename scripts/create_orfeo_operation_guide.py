from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT = Path("output/pdf/12-Codex-Orfeo-SRBbot-operation.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2A6F97")
GREEN = colors.HexColor("#217A4B")
PALE_GREEN = colors.HexColor("#EAF6EF")
PALE_BLUE = colors.HexColor("#EAF3F8")
BODY = colors.HexColor("#23313D")
GRAY = colors.HexColor("#5C6873")
GRID = colors.HexColor("#CCD7DF")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NAVY, spaceAfter=6))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=10, leading=14, textColor=GRAY, spaceAfter=15))
styles.add(ParagraphStyle(name="Heading", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=10, leading=14.2, textColor=BODY, spaceAfter=7))
styles.add(ParagraphStyle(name="Answer", parent=styles["BodyText"], fontSize=10.2, leading=14.5, textColor=NAVY, backColor=PALE_GREEN, borderColor=GREEN, borderWidth=0.8, borderPadding=9, spaceAfter=10))
styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontSize=9.4, leading=13.5, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=0.7, borderPadding=8, spaceBefore=5, spaceAfter=9))
styles.add(ParagraphStyle(name="CodeCustom", parent=styles["Code"], fontName="Courier", fontSize=8.2, leading=11, textColor=colors.HexColor("#17232D"), backColor=colors.HexColor("#F4F6F8"), borderColor=GRID, borderWidth=0.5, borderPadding=8, spaceAfter=9))
styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=8.8, leading=12, textColor=BODY))
styles.add(ParagraphStyle(name="CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.8, leading=12, textColor=colors.white))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(0.72 * inch, 0.55 * inch, 7.78 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.72 * inch, 0.36 * inch, "SRBbot on Orfeo - quick operating guide")
    canvas.drawRightString(7.78 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = [
    Paragraph("SRBbot on Orfeo", styles["DocTitle"]),
    Paragraph("Sleep, wake, reboot, and restart guide | 10 October 2026", styles["Subtitle"]),
    Paragraph("Short answer", styles["Heading"]),
    Paragraph(
        "<b>Wake from ordinary sleep:</b> normally, waking Orfeo is enough. If WSL and the "
        "SRBbot process survived the sleep, the bot resumes polling and automatically catches "
        "up all retained hourly samples.",
        styles["Answer"],
    ),
    Paragraph(
        "<b>After a Windows shutdown or restart:</b> start WSL, then start SRBbot again. "
        "The bot is not currently configured as a Windows auto-start service.",
        styles["Answer"],
    ),
    Paragraph("After rebooting Orfeo", styles["Heading"]),
    Paragraph("Open a WSL terminal, then run:", styles["Body"]),
    Preformatted(
        "cd /home/rudolph/SRBbot\n"
        "bash scripts/start_paper_run.sh",
        styles["CodeCustom"],
    ),
    Paragraph(
        "The script loads the protected Sites credential, uses the existing SQLite database, "
        "and starts the listener in the background. It does not erase or restart the experiment.",
        styles["Body"],
    ),
    Paragraph("Check whether SRBbot is running", styles["Heading"]),
    Preformatted(
        "cd /home/rudolph/SRBbot\n"
        "ps -p $(cat @data/srbbot.pid) -o pid=,stat=,etime=,cmd=",
        styles["CodeCustom"],
    ),
    Paragraph(
        "A displayed process row means the listener is running. If no row appears, run the "
        "start command above. If the start script says it is already running, no further action "
        "is needed.",
        styles["Note"],
    ),
    Paragraph("What happens after sleep?", styles["Heading"]),
    Table(
        [
            [Paragraph("Situation", styles["CellHead"]), Paragraph("Action", styles["CellHead"])],
            [Paragraph("Brief sleep; WSL process survives", styles["Cell"]), Paragraph("Wake Orfeo. SRBbot resumes and catches up automatically.", styles["Cell"])],
            [Paragraph("WSL stopped or bot process ended", styles["Cell"]), Paragraph("Open WSL and run the start command. Catch-up begins from the last saved sample.", styles["Cell"])],
            [Paragraph("Windows reboot or shutdown", styles["Cell"]), Paragraph("Open WSL and run the start command.", styles["Cell"])],
        ],
        colWidths=[2.35 * inch, 4.5 * inch],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    ),
    Spacer(1, 8),
    Paragraph(
        "<b>Important:</b> catch-up depends on the Stage2 server still retaining the missed "
        "samples. For normal overnight or short multi-day interruptions this is suitable. "
        "A longer outage beyond the retention window fails safely and requires inspection; it "
        "will not silently skip missing hours.",
        styles["Note"],
    ),
    Paragraph("Optional stop command", styles["Heading"]),
    Preformatted(
        "cd /home/rudolph/SRBbot\n"
        "bash scripts/stop_paper_run.sh",
        styles["CodeCustom"],
    ),
]

doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.72 * inch,
    leftMargin=0.72 * inch,
    topMargin=0.65 * inch,
    bottomMargin=0.72 * inch,
    title="SRBbot on Orfeo - quick operating guide",
    author="Codex",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT.resolve())
