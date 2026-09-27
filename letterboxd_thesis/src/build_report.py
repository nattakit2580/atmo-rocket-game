"""Generate reports/Letterboxd_Data_Collection_Methodology.pdf (plain academic layout)."""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from methodology_text import FLOW_STEPS, build_sections

styles = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontName="Times-Roman", fontSize=11,
                      leading=15, alignment=TA_LEFT, spaceAfter=7)
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Times-Bold", fontSize=14,
                    spaceBefore=12, spaceAfter=6)
TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName="Times-Bold", fontSize=18, leading=23)
CENTER = ParagraphStyle("Center", parent=BODY, alignment=TA_CENTER)
CAPTION = ParagraphStyle("Caption", parent=BODY, fontName="Times-Italic", fontSize=10,
                         alignment=TA_CENTER, spaceBefore=4)
CELL = ParagraphStyle("Cell", parent=styles["Normal"], fontName="Times-Roman", fontSize=8, leading=10)
CODE = ParagraphStyle("Code", parent=styles["Code"], fontSize=9, leading=12, leftIndent=18,
                      spaceBefore=2, spaceAfter=8)

GRID = TableStyle([
    ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7E6E6")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
])


def _p(text: str, style=BODY) -> Paragraph:
    return Paragraph(escape(text), style)


def _flow_figure():
    rows = []
    for i, step in enumerate(FLOW_STEPS):
        rows.append([step])
        if i < len(FLOW_STEPS) - 1:
            rows.append(["↓"])
    table = Table(rows, colWidths=[7 * cm])
    style = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
             ("FONTSIZE", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 1),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]
    for r in range(0, len(rows), 2):
        style.append(("BOX", (0, r), (0, r), 0.6, colors.black))
    table.setStyle(TableStyle(style))
    return KeepTogether([table, _p("Figure 1. Data collection and sampling flow.", CAPTION)])


def _sampling_table(log):
    head = ["ID", "Film", "Avail.", "Retr.", "Invalid", "English", "Dup.", "Eligible", "Sample", "Status"]
    rows = [head]
    for r in log.itertuples(index=False):
        rows.append([r.movie_id, Paragraph(escape(r.movie_title), CELL), r.total_reviews_available or "n/r",
                     r.population_size, r.invalid_removed, r.english_population, r.duplicates_removed,
                     r.eligible_population, r.sample_obtained,
                     Paragraph(escape(r.collection_status.replace("_", " ")), CELL)])
    t = Table(rows, colWidths=[1.0 * cm, 4.4 * cm, 1.3 * cm, 1.2 * cm, 1.2 * cm, 1.3 * cm, 1.0 * cm,
                               1.4 * cm, 1.3 * cm, 2.9 * cm], repeatRows=1)
    t.setStyle(GRID)
    return t


def _validation_table(report):
    rows = [["Type", "Check", "Result", "Detail"]]
    for r in report.itertuples(index=False):
        rows.append([r.type, Paragraph(escape(r.check), CELL), r.status, Paragraph(escape(r.detail[:180]), CELL)])
    t = Table(rows, colWidths=[2.3 * cm, 6.2 * cm, 2.0 * cm, 6.5 * cm], repeatRows=1)
    t.setStyle(GRID)
    return t


def _schema_table():
    desc = {
        "movie_id": "Film identifier from config/movies.csv (M01-M40)",
        "movie_title": "Film title", "movie_year": "Release year",
        "review_id": "Source identifier, or RID-<SHA-256> of the URL/record when none is supplied",
        "review_text": "Original review text, unmodified",
        "rating": "Star rating 0.5-5.0 if given, else empty",
        "review_date": "Date the review was published/logged (YYYY-MM-DD)",
        "language": "ISO 639-1 code assigned by Lingua (always 'en' in the final dataset)",
        "language_confidence": "Lingua confidence value for that language (0-1)",
        "review_url": "Review URL (blank when --redact-urls is used)",
        "reviewer_id": "SHA-256 pseudonym of the username (optionally salted)",
        "sampling_seed": f"Random seed used for sampling ({config.RANDOM_SEED})",
        "source": "Permitted data source of the record",
        "collected_at": "UTC timestamp at which the record was obtained",
    }
    rows = [["Column", "Description"]] + [[c, Paragraph(escape(desc[c]), CELL)] for c in config.FINAL_COLUMNS]
    t = Table(rows, colWidths=[3.8 * cm, 13.2 * cm], repeatRows=1)
    t.setStyle(GRID)
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Letterboxd Review Dataset - Data Collection Methodology - page {doc.page}")
    canvas.restoreState()


def build_pdf(ctx: dict, path: Path | None = None) -> Path:
    path = path or config.REPORTS_DIR / config.PDF_REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = ctx["data_source"]
    t = ctx["totals"]
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                            title="Letterboxd Data Collection Methodology", author=ds.get("researcher", ""))
    story = [Spacer(1, 2.5 * cm),
             _p("Letterboxd Movie Review Dataset", TITLE),
             _p("Data Collection and Sampling Methodology", CENTER), Spacer(1, 0.8 * cm)]
    for label, key in (("Thesis", "thesis_title"), ("Researcher", "researcher"), ("Institution", "institution")):
        story.append(_p(f"{label}: {ds.get(key, '')}", CENTER))
    story += [_p(f"Report generated: {ctx['run_at']}", CENTER), Spacer(1, 1.2 * cm)]

    summary_rows = [["Item", "Value"],
                    ["Films in study", str(t["movies"])],
                    ["Target reviews per film", str(config.SAMPLE_SIZE_PER_MOVIE)],
                    ["Target total", f"{t['movies'] * config.SAMPLE_SIZE_PER_MOVIE:,}"],
                    ["Language", "English (Lingua)"],
                    ["Sampling", "Simple Random Sampling, per film"],
                    ["Random seed", str(config.RANDOM_SEED)],
                    ["Review records ingested", f"{t['reviews_retrieved']:,}"],
                    ["Eligible English population", f"{t['eligible']:,}"],
                    ["Reviews in final dataset", f"{t['reviews_final']:,}"],
                    ["Films complete / insufficient / awaiting data",
                     f"{t['movies_complete']} / {t['movies_insufficient']} / {t['movies_awaiting']}"]]
    st = Table(summary_rows, colWidths=[8 * cm, 6 * cm])
    st.setStyle(GRID)
    story += [st, _p("Table 0. Study summary (generated from the latest pipeline run).", CAPTION), PageBreak()]

    for heading, paragraphs in build_sections(ctx):
        story.append(_p(heading, H1))
        for para in paragraphs:
            story.append(_p(para))
        if heading.startswith("4."):
            story.append(_flow_figure())
        if heading.startswith("5."):
            story.append(Paragraph(escape(f"eligible = eligible.sort_values('review_id')\n"
                                          f"sample = eligible.sample(n={config.SAMPLE_SIZE_PER_MOVIE}, "
                                          f"random_state={config.RANDOM_SEED})").replace("\n", "<br/>"), CODE))

    story += [PageBreak(), _p("Appendix A. Sampling Log", H1),
              _p("Per-film counts from logs/sampling_log.csv. Avail. = platform-reported number of reviews "
                 "(n/r = not reported by the source); Retr. = records retrieved into the sampling frame; "
                 "Invalid = empty/emoji-only removed; English = English after language identification; "
                 "Dup. = duplicates removed; Eligible = final eligible population; Sample = reviews in the "
                 "final dataset."),
              _sampling_table(ctx["sampling_log"]),
              _p("Appendix B. Validation Results", H1), _validation_table(ctx["validation"]),
              _p("Appendix C. Dataset Schema (letterboxd_reviews_all.csv / Reviews sheet)", H1), _schema_table()]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
