from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from datetime import datetime
import os


def generate_pdf_report(dataset_info, quality_report_text, conversation_history, chart_path=None, output_path="report.pdf"):
    """Generates a PDF report summarizing the dataset, quality, and analysis conversation."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleCustom", parent=styles["Heading1"], fontSize=20, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.grey, fontSize=10, spaceAfter=20)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=14, spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=15)
    code_style = ParagraphStyle("Code", parent=styles["Normal"], fontName="Courier", fontSize=8, backColor=colors.whitesmoke, leading=12)

    elements = []

    elements.append(Paragraph("Data Analysis Report", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))

    elements.append(Paragraph("Dataset Overview", section_style))
    overview_data = [
        ["File name", dataset_info.get("name", "N/A")],
        ["Rows", str(dataset_info.get("rows", "N/A"))],
        ["Columns", str(len(dataset_info.get("columns", [])))],
    ]
    overview_table = Table(overview_data, colWidths=[1.5 * inch, 4 * inch])
    overview_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
    ]))
    elements.append(overview_table)

    elements.append(Paragraph("Columns: " + ", ".join(dataset_info.get("columns", [])), body_style))

    elements.append(Paragraph("Data Quality Summary", section_style))
    quality_lines = quality_report_text.split("\n") if quality_report_text else ["No quality issues detected."]
    for line in quality_lines:
        if line.strip():
            elements.append(Paragraph(line.strip(), body_style))

    if conversation_history:
        elements.append(Paragraph("Analysis Conversation", section_style))
        for turn in conversation_history:
            elements.append(Paragraph(f"<b>Q: {turn['question']}</b>", body_style))
            elements.append(Paragraph(f"A: {turn['answer']}", body_style))
            if turn.get("code"):
                elements.append(Spacer(1, 4))
                elements.append(Paragraph(turn["code"].replace("\n", "<br/>"), code_style))
            elements.append(Spacer(1, 10))

    if chart_path and os.path.exists(chart_path):
        elements.append(Paragraph("Latest Chart", section_style))
        elements.append(Image(chart_path, width=5.5 * inch, height=3.3 * inch))

    doc.build(elements)
    return output_path