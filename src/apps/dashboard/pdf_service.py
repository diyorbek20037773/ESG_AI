# -*- coding: utf-8 -*-
"""Green-finance verdict report — an in-memory PDF (no disk, Railway-friendly)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)

GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#e5484d")
AMBER = colors.HexColor("#d9822b")
INK = colors.HexColor("#141a17")
MUTED = colors.HexColor("#5b6b62")

_VERDICT_COLOR = {"green": GREEN, "not_green": RED, "unknown": AMBER}


def _clean(s):
    return (s or "").replace("’", "'").replace("“", '"').replace("”", '"')


def build_verdict_pdf(analysis) -> bytes:
    """Return the analysis verdict report as PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            title=f"NovdAI ESG {analysis.number}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=INK, fontSize=20, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=MUTED, fontSize=9, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=INK, fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["Normal"], textColor=INK, fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=ss["Normal"], textColor=MUTED, fontSize=8.5, leading=11)

    vcolor = _VERDICT_COLOR.get(analysis.verdict, AMBER)
    vstyle = ParagraphStyle("v", parent=ss["Normal"], textColor=colors.white, fontSize=13,
                            fontName="Helvetica-Bold", alignment=1)

    el = []
    el.append(Paragraph("NovdAI — Yashil moliyalashtirish ESG xulosasi", h1))
    meta = f"Hujjat №: {analysis.number}"
    if analysis.client:
        meta += f" · Mijoz: {_clean(analysis.client.name)}"
    if analysis.company_name:
        meta += f" · Tashkilot: {_clean(analysis.company_name)}"
    meta += f" · Sana: {analysis.created_at:%d.%m.%Y %H:%M}"
    el.append(Paragraph(meta, sub))

    # Verdict banner
    vt = Table([[Paragraph(_clean(analysis.verdict_title) or "NATIJA", vstyle)]],
               colWidths=[doc.width])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), vcolor),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    el.append(vt)
    el.append(Spacer(1, 4))
    el.append(Paragraph(_clean(analysis.summary), body))

    # ESG scores
    el.append(Paragraph("ESG ballari", h2))
    score_tbl = Table([
        ["Ekologiya", "Ijtimoiy", "Boshqaruv", "Umumiy", "Reyting"],
        [analysis.environmental_score, analysis.social_score, analysis.governance_score,
         analysis.overall_score, analysis.rating],
    ], colWidths=[doc.width / 5.0] * 5)
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 13),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (-1, 1), GREEN),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e6ece8")),
    ]))
    el.append(score_tbl)

    def kv_section(title, rows):
        el.append(Paragraph(title, h2))
        data = [[Paragraph(_clean(q), small), Paragraph(_clean(a), small)] for q, a in rows]
        t = Table(data, colWidths=[doc.width * 0.5, doc.width * 0.5])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#eef2ef")),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        el.append(t)

    # Info
    kv_section("1. Asosiy ma'lumotlar", [(i["question"], i["answer"] or "—")
                                         for i in analysis.info_answers])

    # Eco expertise
    rj = analysis.result_json if isinstance(analysis.result_json, dict) else {}
    er = rj.get("eco_required", {})
    eo = rj.get("eco_obtained", {})
    kv_section("2. Ekologik ekspertiza", [
        ("Talab etiladimi?", ("HA" if er.get("value") else "YO'Q") + (f" — {er.get('evidence')}" if er.get("evidence") else "")),
        ("Ijobiy xulosa olinganmi?", ("HA" if eo.get("value") else "YO'Q") + (f" — {eo.get('evidence')}" if eo.get("evidence") else "")),
    ])

    # Stop factors
    def yn(v):
        return "HA" if v else "YO'Q"
    kv_section("3. Stop-faktorlar (istisno faoliyatlar)",
               [(s["question"], yn(s["value"]) + (f" — {s['evidence']}" if s.get("evidence") else ""))
                for s in analysis.stop_factors])

    # Green criteria
    kv_section("4. Yashil mezonlar",
               [(g["question"], yn(g["value"]) + (f" — {g['evidence']}" if g.get("evidence") else ""))
                for g in analysis.green_criteria])

    el.append(Spacer(1, 10))
    el.append(Paragraph("NovdAI — sun'iy intellekt asosidagi yashil moliyalashtirish tahlili. "
                        "Ushbu xulosa qaror qabul qilishda yordamchi vosita sifatida taqdim etiladi.", small))

    doc.build(el)
    return buf.getvalue()
