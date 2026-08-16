from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, HRFlowable
)
from datetime import datetime
import os

ACCENT = colors.HexColor("#00A896")
DARK_TEXT = colors.HexColor("#1A1F26")
MUTED_TEXT = colors.HexColor("#6B7280")
LIGHT_BG = colors.HexColor("#F4F6F8")


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleCustom", parent=styles["Heading1"], fontSize=22, textColor=DARK_TEXT, spaceAfter=4),
        "subtitle": ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=MUTED_TEXT, fontSize=10, spaceAfter=18),
        "section": ParagraphStyle("Section", parent=styles["Heading2"], fontSize=15, textColor=DARK_TEXT, spaceBefore=20, spaceAfter=10),
        "subsection": ParagraphStyle("Subsection", parent=styles["Heading3"], fontSize=12, textColor=ACCENT, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=DARK_TEXT, leading=15),
        "bullet": ParagraphStyle("Bullet", parent=styles["Normal"], fontSize=10, textColor=DARK_TEXT, leading=15, leftIndent=14, bulletIndent=4),
        "question": ParagraphStyle("Question", parent=styles["Normal"], fontSize=11, textColor=DARK_TEXT, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4),
        "answer": ParagraphStyle("Answer", parent=styles["Normal"], fontSize=10, textColor=DARK_TEXT, leading=15, spaceAfter=4),
        "explanation": ParagraphStyle("Explanation", parent=styles["Normal"], fontSize=9.5, textColor=MUTED_TEXT, leading=14, spaceAfter=6, leftIndent=8),
        "kpi_label": ParagraphStyle("KpiLabel", parent=styles["Normal"], fontSize=8.5, textColor=MUTED_TEXT),
        "kpi_value": ParagraphStyle("KpiValue", parent=styles["Normal"], fontSize=16, textColor=ACCENT, fontName="Helvetica-Bold"),
        "chart_caption": ParagraphStyle("ChartCaption", parent=styles["Normal"], fontSize=9, textColor=DARK_TEXT, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
        "table_heading": ParagraphStyle("TableHeading", parent=styles["Heading2"], fontSize=16, textColor=colors.white, spaceAfter=6),
    }


def _divider():
    return HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#E5E7EB"), spaceBefore=4, spaceAfter=4)


def _build_preview_table(columns: list, rows: list, max_cols: int = 6):
    if not rows:
        return None
    display_cols = columns[:max_cols]
    header = [c[:14] for c in display_cols]
    data = [header]
    for row in rows[:5]:
        data.append([str(row.get(c, ""))[:16] for c in display_cols])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _build_kpi_row(kpis: list, styles):
    if not kpis:
        return None
    cells = []
    for k in kpis[:4]:
        label = Paragraph(k.get("label", ""), styles["kpi_label"])
        value = Paragraph(str(k.get("formatted_value", k.get("value", ""))), styles["kpi_value"])
        cells.append([label, value])

    row_data = [[c[0] for c in cells], [c[1] for c in cells]]
    col_width = 6.5 * inch / max(len(cells), 1)
    table = Table(row_data, colWidths=[col_width] * len(cells))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _build_features_list(columns: list, styles):
    """A quick bullet listing of column names — the 'features' overview."""
    elements = [Paragraph("Features", styles["subsection"])]
    chunk = ", ".join(columns[:20]) + ("..." if len(columns) > 20 else "")
    elements.append(Paragraph(f"This dataset includes {len(columns)} features: {chunk}", styles["body"]))
    return elements


def _add_dashboard_block(elements, dashboard_data, chart_images, styles):
    if dashboard_data.get("dashboard_title"):
        elements.append(Paragraph(f"<b>{dashboard_data['dashboard_title']}</b>", styles["subsection"]))
    if dashboard_data.get("domain_reasoning"):
        elements.append(Paragraph(dashboard_data["domain_reasoning"], styles["body"]))
        elements.append(Spacer(1, 10))

    kpi_table = _build_kpi_row(dashboard_data.get("kpis", []), styles)
    if kpi_table:
        elements.append(kpi_table)
        elements.append(Spacer(1, 14))

    anomalies = dashboard_data.get("anomalies", [])
    if anomalies:
        elements.append(Paragraph("Key Observations", styles["subsection"]))
        for a in anomalies:
            elements.append(Paragraph(f"&bull;&nbsp;&nbsp;{a.get('message', '')}", styles["bullet"]))
        elements.append(Spacer(1, 10))

    if chart_images:
        elements.append(Paragraph("Visualizations", styles["subsection"]))
        for title, img_path in chart_images:
            if os.path.exists(img_path):
                elements.append(Paragraph(title, styles["chart_caption"]))
                elements.append(Image(img_path, width=5.2 * inch, height=2.9 * inch))
                elements.append(Spacer(1, 6))


def generate_pdf_report(
    dataset_info: dict,
    quality_text: str,
    preview_rows: list,
    columns: list,
    report_history: list,
    dashboard_data: dict = None,
    dashboard_chart_images: list = None,
    charts_dir: str = None,
    output_path: str = "report.pdf",
    multi_table_sections: list = None,
    ai_summary: str = None,
):
    """
    Order: Cover -> [Preview -> Data Quality -> Features -> AI Summary] -> Dashboard (KPIs +
    charts + observations) -> Q&A with charts (no code/SQL shown).

    For multi-table datasets (multi_table_sections provided), each table gets its own full
    section in that same order, followed by one shared Q&A section at the end.
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    styles = _styles()
    elements = []

    elements.append(Paragraph("Data Analysis Report", styles["title"]))
    elements.append(Paragraph(
        f"{dataset_info.get('name', 'Dataset')} &nbsp;&bull;&nbsp; Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["subtitle"]
    ))
    elements.append(_divider())

    if multi_table_sections:
        elements.append(Paragraph("Dataset Overview", styles["section"]))
        elements.append(Paragraph(
            f"This dataset contains {len(multi_table_sections)} related tables: "
            f"{', '.join(s['table_name'] for s in multi_table_sections)}.",
            styles["body"]
        ))

        for section in multi_table_sections:
            elements.append(PageBreak())

            header_table = Table([[Paragraph(section["table_name"], styles["table_heading"])]], colWidths=[6.9 * inch])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 10))

            if section.get("preview_rows"):
                elements.append(Paragraph("Preview (first 5 rows)", styles["subsection"]))
                preview_table = _build_preview_table(section.get("columns", []), section["preview_rows"])
                if preview_table:
                    elements.append(preview_table)
                elements.append(Spacer(1, 10))

            if section.get("columns"):
                elements.extend(_build_features_list(section["columns"], styles))
                elements.append(Spacer(1, 10))

            if section.get("summary"):
                elements.append(Paragraph("Summary", styles["subsection"]))
                elements.append(Paragraph(section["summary"], styles["body"]))
                elements.append(Spacer(1, 10))

            dd = section.get("dashboard_data")
            if dd and dd.get("widgets"):
                elements.append(_divider())
                _add_dashboard_block(elements, dd, section.get("chart_images", []), styles)

    else:
        if preview_rows:
            elements.append(Paragraph("Dataset Preview", styles["section"]))
            elements.append(Paragraph("First 5 rows of the cleaned dataset.", styles["body"]))
            elements.append(Spacer(1, 8))
            preview_table = _build_preview_table(columns, preview_rows)
            if preview_table:
                elements.append(preview_table)
            elements.append(Spacer(1, 10))

        elements.append(Paragraph("Data Quality", styles["section"]))
        if quality_text and "No automatic cleaning issues" not in quality_text:
            for line in quality_text.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line:
                    elements.append(Paragraph(f"&bull;&nbsp;&nbsp;{line}", styles["bullet"]))
        else:
            elements.append(Paragraph("No data quality issues were detected.", styles["body"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph("Features", styles["section"]))
        rows_display = dataset_info.get("rows", "N/A")
        rows_display = f"{rows_display:,}" if isinstance(rows_display, int) else rows_display
        elements.append(Paragraph(f"&bull;&nbsp;&nbsp;<b>Rows:</b> {rows_display}", styles["bullet"]))
        elements.append(Paragraph(f"&bull;&nbsp;&nbsp;<b>Columns:</b> {len(columns)}", styles["bullet"]))
        elements.append(Paragraph(f"&bull;&nbsp;&nbsp;<b>Column names:</b> {', '.join(columns[:15])}{'...' if len(columns) > 15 else ''}", styles["bullet"]))
        elements.append(Spacer(1, 10))

        if ai_summary:
            elements.append(Paragraph("Summary", styles["section"]))
            elements.append(Paragraph(ai_summary, styles["body"]))

        if dashboard_data and dashboard_data.get("widgets"):
            elements.append(PageBreak())
            elements.append(Paragraph("Dashboard Overview", styles["section"]))
            _add_dashboard_block(elements, dashboard_data, dashboard_chart_images or [], styles)

    if report_history:
        elements.append(PageBreak())
        elements.append(Paragraph("Questions & Answers", styles["section"]))
        elements.append(Paragraph("Every question asked during this session, with the agent's answer.", styles["body"]))

        for i, item in enumerate(report_history, start=1):
            elements.append(_divider())
            elements.append(Paragraph(f"{i}. {item.get('question', '')}", styles["question"]))
            elements.append(Paragraph(item.get("answer", ""), styles["answer"]))

            if item.get("explanation"):
                elements.append(Paragraph(f"<i>{item['explanation']}</i>", styles["explanation"]))

            chart_id = item.get("chart_id")
            if chart_id and charts_dir:
                chart_path = os.path.join(charts_dir, f"{chart_id}.png")
                if os.path.exists(chart_path):
                    elements.append(Spacer(1, 8))
                    elements.append(Image(chart_path, width=5.2 * inch, height=3.1 * inch))

    doc.build(elements)
    return output_path