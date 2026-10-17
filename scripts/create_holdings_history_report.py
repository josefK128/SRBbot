from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAMES = {
    21: "AdTAO", 24: "Quasar", 26: "Perturb", 27: "Orion", 28: "SayGM",
    33: "ReadyAI", 35: "Subnet 35", 41: "Almanac", 48: "Quantum Compute",
    55: "NIOME", 58: "Attune", 67: "Harnyx", 70: "Subnet 70",
    71: "Leadpoet", 72: "StreetVision by NATIX", 75: "Hippius", 76: "Ormas",
    82: "Subnet 82", 94: "Cathedral", 96: "Verathos", 99: "Thirty Spokes",
    103: "Deprecated", 105: "Beam", 107: "Minos", 108: "ChipForge",
    109: "Finsight", 110: "Green Compute", 113: "Subnet 113", 116: "Carbon",
    118: "Ditto",
}

NAVY = colors.HexColor("#18324A")
BLUE = colors.HexColor("#2D6F9F")
ORANGE = colors.HexColor("#D07A28")
GRAY = colors.HexColor("#5D6873")
GRID = colors.HexColor("#D4DCE3")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_GOLD = colors.HexColor("#FFF7E8")
BODY = colors.HexColor("#263440")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=NAVY, alignment=TA_LEFT, spaceAfter=4))
styles.add(ParagraphStyle(name="SubtitleX", parent=styles["Normal"], fontSize=9, leading=12, textColor=GRAY, spaceAfter=10))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontSize=8.4, leading=11.5, textColor=BODY, spaceAfter=5))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=6.7, leading=8.2, textColor=GRAY))
styles.add(ParagraphStyle(name="CellX", parent=styles["BodyText"], fontSize=7.1, leading=8.5, textColor=BODY))
styles.add(ParagraphStyle(name="HeaderX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=colors.white))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontSize=8.6, leading=11.7, textColor=NAVY, backColor=PALE_BLUE, borderColor=BLUE, borderWidth=.7, borderPadding=7, spaceAfter=8))


def p(text, style="BodyX"):
    return Paragraph(str(text), styles[style])


def held_label(netuid: int, changed: bool) -> str:
    name = NAMES.get(netuid, "Name unavailable")
    marker = " *" if changed else ""
    return f"{name} (SN{netuid}){marker}"


def load(db_path: Path):
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT s.sampled_at,s.tao_market,"
        "MAX(CASE WHEN n.strategy='score' THEN n.held_netuid END) score_netuid,"
        "MAX(CASE WHEN n.strategy='breakout' THEN n.held_netuid END) breakout_netuid,"
        "MAX(CASE WHEN d.strategy='score' THEN d.action END) score_action,"
        "MAX(CASE WHEN d.strategy='breakout' THEN d.action END) breakout_action "
        "FROM snapshots s JOIN positions_nav n USING(snapshot_id) "
        "JOIN decisions d ON d.snapshot_id=s.snapshot_id "
        "GROUP BY s.snapshot_id,s.sampled_at,s.tao_market ORDER BY s.sampled_at"
    ).fetchall()
    con.close()
    return rows


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(.55 * inch, .48 * inch, 10.45 * inch, .48 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(.55 * inch, .29 * inch, "SRBbot post-decision holdings by sample")
    canvas.drawRightString(10.45 * inch, .29 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(db_path: Path, output: Path):
    rows = load(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.fromisoformat(rows[0]["sampled_at"]).strftime("%b %d, %Y %H:%M UTC")
    end = datetime.fromisoformat(rows[-1]["sampled_at"]).strftime("%b %d, %Y %H:%M UTC")
    regime = {None: "Initial", -1: "Falling", 0: "Static", 1: "Rising"}
    data = [[p("#", "HeaderX"), p("Sample time (UTC)", "HeaderX"), p("Tao condition", "HeaderX"), p("Score holding after decision", "HeaderX"), p("Breakout holding after decision", "HeaderX")]]
    for index, row in enumerate(rows, 1):
        score_changed = row["score_action"] in ("ENTER", "REPLACE")
        breakout_changed = row["breakout_action"] in ("ENTER", "REPLACE")
        timestamp = datetime.fromisoformat(row["sampled_at"]).strftime("%b %d %H:%M")
        data.append([
            p(index, "CellX"), p(timestamp, "CellX"), p(regime[row["tao_market"]], "CellX"),
            p(held_label(row["score_netuid"], score_changed), "CellX"),
            p(held_label(row["breakout_netuid"], breakout_changed), "CellX"),
        ])
    table = Table(data, colWidths=[.38*inch, 1.35*inch, 1.0*inch, 3.35*inch, 3.35*inch], repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), .4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.7),
        ("ALIGN", (0, 1), (0, -1), "RIGHT"),
    ]
    for index, row in enumerate(rows, 1):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#F7F9FB")))
        if row["score_action"] in ("ENTER", "REPLACE"):
            commands.append(("BACKGROUND", (3, index), (3, index), PALE_BLUE))
        if row["breakout_action"] in ("ENTER", "REPLACE"):
            commands.append(("BACKGROUND", (4, index), (4, index), PALE_GOLD))
    table.setStyle(TableStyle(commands))
    story = [
        p("SRBbot holdings after every sample", "TitleX"),
        p(f"Score and Breakout | {len(rows)} accepted samples | {start} to {end}", "SubtitleX"),
        p("Each row shows the subnet held <b>after</b> that sample's decision and any resulting simulated stake replacement. An asterisk and colored cell indicate an initial entry or replacement at that sample.", "CalloutX"),
        table,
        Spacer(1, 6),
        p("Name note: SRBbot's journal stores netuids, not subnet names. Names shown here are a current directory lookup and may differ from historical branding; netuid is the authoritative identifier. 'Subnet 35,' 'Subnet 70,' 'Subnet 82,' and 'Subnet 113' are the directory's current generic labels; SN103 is currently labeled Deprecated. Name source: Bittensor.ai Subnet Directory (https://bittensor.ai/subnets/), retrieved Oct 13, 2026.", "SmallX"),
    ]
    doc = SimpleDocTemplate(str(output), pagesize=landscape(letter), leftMargin=.55*inch, rightMargin=.55*inch, topMargin=.5*inch, bottomMargin=.62*inch, title="SRBbot holdings after every sample", author="Codex")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.db, args.output)
